import src.external.prometheus.prometheus_client as prom_cli

def collect_system_metrics(resource, model, duration):
    df = prom_cli.query_prometheus(model, resource, duration)

    df = df[~df["pod"].str.contains("unknown|kube|chaos|prometheus|istio", case=False)]
    df = df.set_index(["pod", "timestamp"]).sort_index()

    return df