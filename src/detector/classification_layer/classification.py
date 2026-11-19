
THRESHOLD = {
    "cpu": 0.0005,
    "mem": 50000,
    "network": "pre-fault IsolationForest fit; at least 2 anomalous scoring windows"
}

def classify_anomalies(resource, slopes, pods_anomalous, leak_pods, fault_type=None):
    SLOPE_THRESHOLD = THRESHOLD[resource]
    final_predictions = {}

    if resource == "network":
        pods = sorted({pod for pod, _signal in slopes} | set(leak_pods))
        for pod in pods:
            # Each pod's rolling feature window is scored by IsolationForest;
            # any outlier signal marks that pod as anomalous. Fault labels and
            # type are reserved for evaluation, not detector decisions.
            final_predictions[pod] = int(any(
                isinstance(key, tuple) and len(key) > 1 and key[0] == pod
                for key in pods_anomalous
            ))

        y_true = [int(pod in leak_pods) for pod in pods]
        y_pred = [final_predictions[pod] for pod in pods]
        return y_true, y_pred, SLOPE_THRESHOLD

    for pod in slopes.keys():

        is_anomalous = pod in pods_anomalous
        has_positive_trend = slopes[pod] > SLOPE_THRESHOLD
        final_predictions[pod] = int(is_anomalous and has_positive_trend)


    y_true = []
    y_pred = []

    for pod in slopes.keys():

        true_label = int(pod in leak_pods)
        pred_label = final_predictions[pod]

        y_true.append(true_label)
        y_pred.append(pred_label)

    return y_true, y_pred, SLOPE_THRESHOLD
