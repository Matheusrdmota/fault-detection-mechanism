
THRESHOLD = {
    "cpu": 0.0005,
    "mem": 50000
}

def classify_anomalies(resource, slopes, pods_anomalous, leak_pods):
    SLOPE_THRESHOLD = THRESHOLD[resource]
    final_predictions = {}

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