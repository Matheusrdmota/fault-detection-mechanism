import src.config.kubernetes.k8s_config as k8s_config
import src.external.prometheus.prometheus_client as prom_cli
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
import numpy as np
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

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

def detect(resource, duration):
    pods_anomalous = run_isolation_forest(resource, duration)
    slopes = run_linear_regression(resource, duration)

    return pods_anomalous, slopes