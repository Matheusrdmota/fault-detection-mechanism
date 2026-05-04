import src.config.kubernetes.k8s_config as k8s_config
import src.external.prometheus.prometheus_client as prom_cli
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

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

    df_reg = df_reg[~df_reg["pod"].str.contains("unknown|kube|chaos|prometheus|istio", case=False)]
    df_reg = df_reg.set_index(["pod", "timestamp"]).sort_index()

    slopes = {}

    for pod in df_reg.index.get_level_values("pod").unique():

        pod_df = df_reg.xs(pod, level="pod").sort_index()

        if len(pod_df) < 5:
            continue

        time_seconds = pod_df.index.astype("int64") // 10**9
        time_seconds = time_seconds - time_seconds.min()

        X = time_seconds.values.reshape(-1, 1)
        y = pod_df["value"].values

        model = LinearRegression()
        model.fit(X, y)

        slope = model.coef_[0]
        slopes[pod] = slope

    print(slopes)
    
    return slopes

def detect(resource, duration):
    pods_anomalous = run_isolation_forest(resource, duration)
    slopes = run_linear_regression(resource, duration)

    return pods_anomalous, slopes