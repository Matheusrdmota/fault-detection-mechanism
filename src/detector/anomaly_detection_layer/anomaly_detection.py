import src.external.prometheus.prometheus_client as prom_cli
from sklearn.ensemble import IsolationForest
import numpy as np
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
import pandas as pd

def run_isolation_forest(resource, duration):
    df_if = prom_cli.query_prometheus("iforest", resource, duration)

    iso_model = IsolationForest(contamination=0.1, random_state=42)
    df_if["anomaly"] = iso_model.fit_predict(df_if[["value"]])

    anomaly_ratio = (
        df_if.groupby("pod")["anomaly"]
        .apply(lambda x: (x == -1).mean())
    )

    print(df_if[df_if["anomaly"] == -1])

    threshold = 0.01

    pods_anomalous = anomaly_ratio[anomaly_ratio >= threshold].index.tolist()
    print(pods_anomalous)
    return pods_anomalous


def run_linear_regression(resource, duration):
    df_reg = prom_cli.query_prometheus("regression", resource, duration)

    df_reg = df_reg[
        ~df_reg["pod"].str.contains(
            "unknown|kube|chaos|prometheus|istio",
            case=False
        )
    ]
    df_reg = df_reg.set_index(["pod", "timestamp"]).sort_index()

    slopes = {}

    for pod in df_reg.index.get_level_values("pod").unique():

        pod_df = df_reg.xs(pod, level="pod").sort_index()

        if len(pod_df) < 5:
            continue

        x = pod_df.index.astype("int64") // 10**9
        x = (x - x.min()).astype(float)

        y = pod_df["value"].astype(float).values

        n = len(x)

        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x ** 2)

        denominator = n * sum_x2 - (sum_x ** 2)

        if denominator == 0:
            continue

        slope = (n * sum_xy - sum_x * sum_y) / denominator

        slopes[pod] = slope

    print(slopes)

    return slopes


def run_network_change_detection(duration, latency_samples=None, fault_start_time=None, target_pod=None, fault_type=None):
    """Detect network anomalies from unlabeled rolling metric windows.

    fault_start_time and fault_type remain accepted for compatibility with the
    experiment runner, but are deliberately not used by this detector.
    """
    df = prom_cli.query_prometheus("regression", "network", duration)
    df = df[~df["pod"].str.contains(
        "unknown|kube|chaos|prometheus|istio", case=False
    )]

    anomalous_signals = set()
    signal_stats = {}
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        for pod, pod_df in df.dropna(subset=["value"]).groupby("pod"):
            features = pod_df.pivot_table(
                index="timestamp", columns="signal", values="value", aggfunc="mean"
            ).sort_index().ffill().fillna(0.0)
            if len(features) < 5 or features.shape[1] == 0:
                continue
            model = IsolationForest(contamination=0.1, random_state=42)
            scaled = StandardScaler().fit_transform(features)
            labels = model.fit_predict(scaled)
            recent_anomaly = labels[-3:].tolist().count(-1) >= min(2, len(labels[-3:]))
            for signal in features.columns:
                values = features[signal]
                signal_stats[(pod, signal)] = {
                    "baseline_median": float(values.median()),
                    "affected_median": float(values.iloc[-max(1, len(values) // 10):].median()),
                    "relative_change": 0.0,
                }
            if recent_anomaly:
                for signal in features.columns:
                    anomalous_signals.add((pod, signal))

    # HTTP probe windows are evaluated by the same unsupervised model; neither
    # the known injection time nor the injected fault type defines the windows.
    if latency_samples:
        records = []
        default_pod = target_pod[0] if isinstance(target_pod, (list, tuple)) else target_pod
        for sample in latency_samples:
            if len(sample) == 4:
                timestamp, pod, latency, success_ratio = sample
            else:
                timestamp, latency, success_ratio = sample
                pod = default_pod
            records.append((timestamp, pod, latency, success_ratio))
        samples = pd.DataFrame(
            records,
            columns=["timestamp", "pod", "latency_seconds", "success_ratio"],
        )
        samples["timestamp"] = pd.to_datetime(samples["timestamp"], unit="s", utc=True)
        samples["requests_per_second"] = (
            samples.success_ratio.astype(float) * 4.0
            / samples.latency_seconds.astype(float).clip(lower=1e-6)
        )
        http_columns = [
            "latency_seconds", "success_ratio", "requests_per_second"
        ]
        for pod, pod_samples in samples.dropna(subset=["pod"]).groupby("pod"):
            http_features = pod_samples.set_index("timestamp")[http_columns].rename(columns={
                "latency_seconds": "http_latency",
                "success_ratio": "http_success_ratio",
                "requests_per_second": "http_requests_per_second",
            }).sort_index()
            if len(http_features) < 5:
                continue
            scaled = StandardScaler().fit_transform(http_features)
            labels = IsolationForest(contamination=0.1, random_state=42).fit_predict(scaled)
            recent_anomaly = labels[-3:].tolist().count(-1) >= min(2, len(labels[-3:]))
            anomalous_rows = http_features.loc[labels == -1]
            for signal in http_features.columns:
                values = http_features[signal]
                signal_stats[(pod, signal)] = {
                    "baseline_median": float(values.median()),
                    "affected_median": float(anomalous_rows[signal].median()) if not anomalous_rows.empty else float(values.median()),
                    "relative_change": 0.0,
                }
                if recent_anomaly:
                    anomalous_signals.add((pod, signal))

    print("HTTP latency baseline/affected:", {
        key: value for key, value in signal_stats.items() if key[1] == "http_latency"
    })
    print("Network fault signals:", sorted(anomalous_signals))
    return anomalous_signals, signal_stats


def run_network_isolation_forest(training_data, scoring_data, contamination=0.01,
                                 min_anomalous_windows=2):
    """Fit per-pod network Isolation Forests on normal data and score new data.

    Both arguments must be dataframes with ``pod``, ``signal`` and ``value``
    columns (and optionally ``timestamp``). ``training_data`` should contain
    only representative fault-free observations. Models are fitted exclusively
    on that dataframe and then applied to ``scoring_data``.

    Returns ``(anomalous_signals, models, diagnostics)``. An entry in
    ``anomalous_signals`` is a ``(pod, signal)`` pair. Each pod is reported only
    when at least ``min_anomalous_windows`` scoring rows are classified as
    outliers, limiting alerts from isolated spikes.
    """
    required = {"pod", "signal", "value"}
    for name, frame in (("training_data", training_data), ("scoring_data", scoring_data)):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{name} is missing required columns: {sorted(missing)}")

    def make_features(frame):
        feature_columns = ["pod", "signal", "value"]
        if "timestamp" in frame.columns:
            feature_columns.append("timestamp")
        data = frame.loc[:, feature_columns].copy()
        data["value"] = pd.to_numeric(data["value"], errors="coerce")
        data = data.dropna(subset=["pod", "signal", "value"])
        feature_frames = {}
        for pod, pod_data in data.groupby("pod"):
            if "timestamp" in frame.columns:
                features = pod_data.pivot_table(
                    index="timestamp", columns="signal", values="value", aggfunc="mean"
                ).sort_index()
            else:
                # Without timestamps, each input row is treated as a sample.
                pod_data = pod_data.assign(_sample=pod_data.index)
                features = pod_data.pivot_table(
                    index="_sample", columns="signal", values="value", aggfunc="mean"
                ).sort_index()
            feature_frames[pod] = features
        return feature_frames

    training_features = make_features(training_data)
    scoring_features = make_features(scoring_data)
    models = {}
    diagnostics = {}
    anomalous_signals = set()

    for pod, train in training_features.items():
        train = train.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all")
        train = train.fillna(train.median()).fillna(0.0)
        if len(train) < 5 or train.shape[1] == 0:
            continue

        columns = list(train.columns)
        scaler = StandardScaler().fit(train[columns])
        model = IsolationForest(contamination=contamination, random_state=42)
        model.fit(scaler.transform(train[columns]))
        models[pod] = {"scaler": scaler, "model": model, "columns": columns,
                       "fill_values": train.median().to_dict()}

        score = scoring_features.get(pod)
        if score is None:
            continue
        score = score.reindex(columns=columns)
        score = score.replace([np.inf, -np.inf], np.nan)
        score = score.fillna(models[pod]["fill_values"]).fillna(0.0)
        labels = model.predict(scaler.transform(score[columns]))
        anomaly_rows = score.loc[labels == -1]
        anomalous_count = int((labels == -1).sum())
        for signal in columns:
            baseline_median = float(train[signal].median())
            scoring_median = float(score[signal].median())
            diagnostics[(pod, signal)] = {
                "baseline_median": baseline_median,
                "affected_median": scoring_median,
                "relative_change": (scoring_median - baseline_median)
                    / max(abs(baseline_median), 1e-9),
                "scoring_windows": int(len(score)),
                "anomalous_windows": anomalous_count,
            }
        if int((labels == -1).sum()) >= min_anomalous_windows:
            for signal in columns:
                if not anomaly_rows.empty:
                    anomalous_signals.add((pod, signal))

    return anomalous_signals, models, diagnostics

def detect(resource, duration, latency_samples=None, fault_start_time=None, target_pod=None, fault_type=None):
    if resource == "network":
        return run_network_change_detection(
            duration, latency_samples, fault_start_time, target_pod, fault_type
        )

    pods_anomalous = run_isolation_forest(resource, duration)
    slopes = run_linear_regression(resource, duration)

    return pods_anomalous, slopes
