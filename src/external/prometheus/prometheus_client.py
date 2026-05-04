import time
import requests
import pandas as pd

PROM_URL = "http://localhost:9090/api/v1/query_range"

namespace = "sock-shop"
STEP = "2s"
STEP_ISOLATION = "5s"

queries = {
   "cpu": {
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
    "mem": {
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
    }
}

def query_prometheus(model, type, duration):
    step = ""
    if model == "iforest":
      step = STEP_ISOLATION
    else:
      step = STEP

    end = time.time() - 35
    start = end - duration - 15

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
        for ts, val in r["values"]:
            records.append((
                pd.to_datetime(float(ts), unit="s"),
                pod,
                float(val)
            ))

    return pd.DataFrame(records, columns=["timestamp", "pod", "value"])