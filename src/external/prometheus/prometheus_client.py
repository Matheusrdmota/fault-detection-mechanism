import time
import requests
import pandas as pd

PROM_URL = "http://localhost:9090/api/v1/query_range"

namespace = "sock-shop"
STEP = "2s"
STEP_ISOLATION = "5s"

queries = {
   "mem": {
        "iforest": f'''
            sum by (pod) (
              deriv(container_memory_working_set_bytes{{namespace="{namespace}",pod!=""}}[3m]) > 0
            )
          ''',
        "regression": f'''
            sum by (pod) (
              container_memory_working_set_bytes{{namespace="{namespace}",pod!=""}}
            )
          '''
    },
    "cpu": {
        "iforest": f'''
            sum by (pod) (
              rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod!=""}}[3m])
            )
          ''',
        "regression": f'''
            sum by (pod) (
              rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod!=""}}[3m])
            )
          '''
    },
    # kpod metrics are emitted with per-container labels even though they
    # report the pod network namespace. Select eth0 and max by pod to avoid
    # counting the same interface once per container (or including loopback).
    "network": {
        "iforest": f'''label_replace(max by (pod) (
            rate(kpod_net_iface_tx_bytes_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "tx_bytes", "pod", ".*")
        or label_replace(max by (pod) (
            rate(kpod_net_iface_tx_packets_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "tx_packets", "pod", ".*")
        or label_replace(max by (pod) (
            rate(kpod_net_iface_rx_drops_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "rx_drops", "pod", ".*")
        or label_replace(max by (pod) (
            rate(kpod_net_iface_tx_drops_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "tx_drops", "pod", ".*")''',
        "regression": f'''label_replace(max by (pod) (
            rate(kpod_net_iface_tx_bytes_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "tx_bytes", "pod", ".*")
        or label_replace(max by (pod) (
            rate(kpod_net_iface_tx_packets_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "tx_packets", "pod", ".*")
        or label_replace(max by (pod) (
            rate(kpod_net_iface_rx_drops_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "rx_drops", "pod", ".*")
        or label_replace(max by (pod) (
            rate(kpod_net_iface_tx_drops_total{{namespace="{namespace}",pod!="",interface="eth0"}}[2m])
        ), "signal", "tx_drops", "pod", ".*")'''
    }
}

def query_prometheus(model, type, duration):
    step = ""
    if model == "iforest":
      step = STEP_ISOLATION
    else:
      step = STEP

    end = time.time() - 35
    # Keep a clean pre-fault baseline: injection starts after a 60s baseline
    # (the additional 10s accounts for the experiment's post-injection wait).
    start = end - duration - (60 if type == "network" else 15)

    response = requests.get(
        PROM_URL,
        params={
            "query": queries[type][model],
            "start": start,
            "end": end,
            "step": step
        }
    )

    results = response.json()["data"]["result"]
    records = []

    for r in results:
        pod = r["metric"].get("pod", "unknown")
        signal = r["metric"].get("signal", "value")
        for ts, val in r["values"]:
            records.append((
                pd.to_datetime(float(ts), unit="s"),
                pod,
                signal,
                float(val)
            ))

    return pd.DataFrame(records, columns=["timestamp", "pod", "signal", "value"])
