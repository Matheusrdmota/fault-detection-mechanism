import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
import os
import time
import src.detector.anomaly_detection_layer.anomaly_detection as detection
import src.detector.classification_layer.classification as classification

OUTPUT_FILE = os.path.join(
    r"/home/matheus/fault-detector/results",
    "memory_leak_experiments_results.csv"
)

OUTPUT_FILE_CPU = os.path.join(
    r"/home/matheus/fault-detector/results",
    "cpu_experiments_results.csv"
)

def save_to_excel(resource, result):

    df = pd.DataFrame([result])
    file_exists = ""
    output_file = ""
    if resource == "mem":
        file_exists = os.path.exists(OUTPUT_FILE_CPU)
        output_file = OUTPUT_FILE
    else:
        file_exists = os.path.exists(OUTPUT_FILE)
        output_file = OUTPUT_FILE_CPU

    
    df.to_csv(
        output_file,
        mode="a",
        header=not file_exists,
        index=False
    )

def detection_init(resource, chaos_config, chaos_name):
    leak_pods = []

    start_time = time.time()
    if chaos_config['leak_injected']:
        leak_pods.extend(chaos_config["pod"])

    pods_anomalous, slopes = detection.detect(resource, chaos_config["duration"])
    y_true, y_pred, slope_threshold = classification.classify_anomalies(resource, slopes, pods_anomalous, leak_pods)

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
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)

    end_time = time.time()

    summary = {
        "experiment_id": f"{chaos_name}_{int(time.time())}",
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

    return summary