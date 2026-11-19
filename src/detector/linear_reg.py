import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
import os
import time
import threading
import src.detector.anomaly_detection_layer.anomaly_detection as detection
import src.detector.classification_layer.classification as classification

RESULTS_LOCK = threading.Lock()

# OUTPUT_FILE = os.path.join(
#     r"/home/matheus/fault-detector/results",
#     "memory_leak_experiments_results.csv"
# )

# OUTPUT_FILE_CPU = os.path.join(
#     r"/home/matheus/fault-detector/results",
#     "cpu_experiments_results.csv"
# )

OUTPUT_FILE = os.path.join(
    r"/home/matheus/fault-detector/results",
    "memory_leak_experiments_results_cloud.csv"
)

OUTPUT_FILE_CPU = os.path.join(
    r"/home/matheus/fault-detector/results",
    "cpu_experiments_results_svm.csv"
)
OUTPUT_FILE_CPU_HOG = os.path.join(
    r"/home/matheus/fault-detector/results",
    "cpu_experiments_results_cloud.csv"
)
OUTPUT_FILE_NETWORK = os.path.join(
    r"/home/matheus/fault-detector/results",
    "network_fault_detection_results.csv"
)
OUTPUT_FILE_PACKET_LOSS_CLOUD = os.path.join(
    r"/home/matheus/fault-detector/results",
    "network_packet_loss_results_cloud.csv"
)
OUTPUT_FILE_DELAY_CLOUD = os.path.join(
    r"/home/matheus/fault-detector/results",
    "network_delay_results_cloud.csv"
)
OUTPUT_FILE_LONG_RESPONSE_TIME = os.path.join(
    r"/home/matheus/fault-detector/results",
    "long_response_time_results.csv"
)
OUTPUT_FILE_NETWORK_DIAGNOSTICS = os.path.join(
    r"/home/matheus/fault-detector/results",
    "network_fault_detection_signal_diagnostics.csv"
)

def save_to_excel(resource, result):

    df = pd.DataFrame([result])
    file_exists = ""
    output_file = ""
    if resource == "network":
        fault_type = result.get("fault_type")
        output_file = {
            "long_response_time": OUTPUT_FILE_LONG_RESPONSE_TIME,
            "packet_loss": OUTPUT_FILE_PACKET_LOSS_CLOUD,
            "delay": OUTPUT_FILE_DELAY_CLOUD,
        }.get(fault_type, OUTPUT_FILE_NETWORK)
        file_exists = os.path.exists(output_file)
    elif resource == "mem":
        file_exists = os.path.exists(OUTPUT_FILE)
        output_file = OUTPUT_FILE
    else:
        output_file = (
            OUTPUT_FILE_CPU_HOG
            if result.get("fault_type") == "cpu_hog"
            else OUTPUT_FILE_CPU
        )
        file_exists = os.path.exists(output_file)

    
    with RESULTS_LOCK:
        file_exists = os.path.exists(output_file)
        df.to_csv(
            output_file,
            mode="a",
            header=not file_exists,
            index=False
        )


def save_network_diagnostics(experiment_id, signal_stats, detected_signals):
    records = []
    for (pod, signal), stats in signal_stats.items():
        records.append({
            "experiment_id": experiment_id,
            "pod": pod,
            "signal": signal,
            "baseline_median": stats["baseline_median"],
            "affected_median": stats["affected_median"],
            "relative_change": stats["relative_change"],
            "detected": int(
                (pod, signal) in detected_signals
                or (signal.endswith("_drops") and (pod, f"{signal}_strong") in detected_signals)
            )
        })

    if records:
        with RESULTS_LOCK:
            file_exists = os.path.exists(OUTPUT_FILE_NETWORK_DIAGNOSTICS)
            pd.DataFrame(records).to_csv(
                OUTPUT_FILE_NETWORK_DIAGNOSTICS,
                mode="a",
                header=not file_exists,
                index=False
            )

def detection_init(resource, chaos_config, chaos_name, latency_samples=None, fault_start_time=None, target_pod=None, fault_type=None, network_training_data=None, evaluation_excluded_pods=None):
    fault_pods = []

    start_time = time.time()
    if chaos_config['leak_injected']:
        fault_pods.extend(chaos_config["pod"])

    if resource == "network":
        training_data = (
            network_training_data.copy()
            if network_training_data is not None
            else pd.DataFrame(columns=["timestamp", "pod", "signal", "value"])
        )
        if not training_data.empty:
            training_data["timestamp"] = pd.to_datetime(training_data["timestamp"], utc=True)
            training_cutoff = training_data["timestamp"].max()
        elif fault_start_time is not None:
            # Prometheus may not expose the optional kpod interface series.
            # In that case, use the direct HTTP probe samples gathered before
            # injection as the target pod's unsupervised training baseline.
            training_cutoff = pd.to_datetime(fault_start_time, unit="s", utc=True)
            print("No Prometheus network series in baseline; using pre-fault HTTP probes.")
        else:
            raise ValueError(
                "Network detection needs Prometheus baseline data or a fault start time"
            )
        scoring_data = detection.prom_cli.query_prometheus(
            "regression", "network", chaos_config["duration"]
        )
        scoring_data["timestamp"] = pd.to_datetime(scoring_data["timestamp"], utc=True)
        # Start scoring after the most recent observation used for training.
        # The model itself receives no injection timestamp or fault type.
        scoring_data = scoring_data[scoring_data["timestamp"] > training_cutoff].copy()

        target_pods = (
            list(target_pod) if isinstance(target_pod, (list, tuple, set))
            else [target_pod] if target_pod else []
        )
        if latency_samples and target_pods:
            http_records = []
            for sample in latency_samples:
                if len(sample) == 4:
                    timestamp, sample_pod, latency, success_ratio = sample
                else:
                    timestamp, latency, success_ratio = sample
                    sample_pod = target_pods[0]
                timestamp = pd.to_datetime(timestamp, unit="s", utc=True)
                requests_per_second = float(success_ratio) * 4.0 / max(float(latency), 1e-6)
                for signal, value in (
                    ("http_latency", latency),
                    ("http_success_ratio", success_ratio),
                    ("http_requests_per_second", requests_per_second),
                ):
                    http_records.append({
                        "timestamp": timestamp,
                        "pod": sample_pod,
                        "signal": signal,
                        "value": value,
                    })
            http_data = pd.DataFrame(http_records)
            pre_fault_http = http_data[http_data["timestamp"] <= training_cutoff]
            per_pod_windows = pre_fault_http.groupby("pod")["timestamp"].nunique()
            missing_baselines = [
                pod for pod in target_pods if per_pod_windows.get(pod, 0) < 5
            ]
            if missing_baselines:
                raise ValueError(
                    "Network detection needs at least five pre-fault HTTP probe windows "
                    f"for each target; insufficient baseline for {missing_baselines}"
                )
            training_data = pd.concat([
                training_data,
                pre_fault_http,
            ], ignore_index=True)
            scoring_data = pd.concat([
                scoring_data,
                http_data[http_data["timestamp"] > training_cutoff],
            ], ignore_index=True)

        if training_data.empty:
            raise ValueError(
                "Network detection has no Prometheus baseline or pre-fault HTTP probes"
            )

        pods_anomalous, models, slopes = detection.run_network_isolation_forest(
            training_data,
            scoring_data,
            contamination=0.01,
            min_anomalous_windows=2,
        )
        excluded = set(evaluation_excluded_pods or ())
        if excluded:
            slopes = {key: value for key, value in slopes.items() if key[0] not in excluded}
            pods_anomalous = {
                item for item in pods_anomalous if item[0] not in excluded
            }
        slope_threshold = "IsolationForest contamination=0.01; at least 2 anomalous windows"
        print(f"Network Isolation Forest models fitted: {len(models)}")
        print("Network Isolation Forest flagged pods:", sorted({pod for pod, _ in pods_anomalous}))
    else:
        pods_anomalous, slopes = detection.detect(
            resource,
            chaos_config["duration"],
            latency_samples=latency_samples,
            fault_start_time=fault_start_time,
            target_pod=target_pod,
            fault_type=fault_type,
        )
        slope_threshold = classification.THRESHOLD[resource]
    y_true, y_pred, slope_threshold = classification.classify_anomalies(
        resource, slopes, pods_anomalous, fault_pods, fault_type
    )

    all_y_true = []
    all_y_pred = []

    all_y_true.append(y_true)
    all_y_pred.append(y_pred)

    report = classification_report(y_true, 
                                    y_pred, 
                                    labels=[0,1], 
                                    zero_division=0, 
                                    output_dict=True)
    print("\nClassification Report:")
    print(report)

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_true, y_pred, labels=[0,1]))

    cm = confusion_matrix(y_true, y_pred, labels=[0,1])
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    end_time = time.time()

    summary = {
        "experiment_id": f"{chaos_name}_{int(time.time())}"
            + (f"_{chaos_config['latency']}" if chaos_config.get("latency") else ""),
        "fault_type": fault_type or chaos_config.get("fault_type", "unknown"),
        "leak_injected": f"{chaos_config['leak_injected']}",
        "threshold": slope_threshold,
        "duration": end_time - start_time,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "true_negative": cm[0][0],
        "false_positive": cm[0][1],
        "false_negative": cm[1][0],
        "true_positive": cm[1][1],
        "precision_class_0": report['0']["precision"],
        "recall_class_0": report['0']["recall"],
        "f1_class_0": report['0']["f1-score"],
        "precision_class_1": report['1']["precision"],
        "recall_class_1": report['1']["recall"],
        "f1_class_1": report['1']["f1-score"],            
    }        
    save_to_excel(resource, summary)
    if resource == "network":
        save_network_diagnostics(
            summary["experiment_id"], slopes, pods_anomalous
        )

    return summary
