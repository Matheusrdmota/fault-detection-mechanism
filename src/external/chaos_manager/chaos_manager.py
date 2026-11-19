import random
import subprocess
import time
import os
import tempfile
import yaml
import json

def apply_chaos(config):

    if not config["leak_injected"]:
        return None

    name = ""
    chaos_yaml = {}
    if config["resource"] == "network":
        fault_type = config.get("fault_type", "packet_loss")
        name = f"network-{fault_type.replace('_', '-')}-{random.randint(1,100000)}"
        if fault_type == "packet_loss":
            action = "loss"
            fault_spec = {
                "loss": config.get("loss", "10%"),
                "correlation": "0",
            }
        elif fault_type == "congestion":
            action = "bandwidth"
            fault_spec = {
                "rate": config.get("rate", "64kbps"),
                "limit": 65536,
                "buffer": 65536,
            }
        elif fault_type in ("delay", "long_response_time"):
            action = "delay"
            fault_spec = {
                "latency": config.get(
                    "latency",
                    "1000ms" if fault_type == "long_response_time" else "200ms",
                ),
                "correlation": config.get("correlation", "0"),
                "jitter": config.get("jitter", "0ms"),
            }
        else:
            raise ValueError(f"Unsupported network fault type: {fault_type}")
        chaos_yaml = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": {"name": name, "namespace": "sock-shop"},
            "spec": {
                "action": action,
                "mode": "all",
                "selector": {
                    "namespaces": ["sock-shop"],
                    "pods": {"sock-shop": config["pod"]}
                },
                **({"loss": fault_spec} if action == "loss" else
                   {"bandwidth": fault_spec} if action == "bandwidth" else
                   {"delay": fault_spec}),
                "duration": f'{config["duration"]}s'
            }
        }
    elif config["resource"] == "mem":
        name = f"memory-chaos-{random.randint(1,100000)}"
        chaos_yaml = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {"name": name, "namespace": "sock-shop"},
            "spec": {
                "mode": "all",
                "selector": {
                    "namespaces": ["sock-shop"],
                    "pods": {
                        "sock-shop": config["pod"]
                    }
                },
                "stressors": {
                    "memory": {
                        "workers": 1,
                        "size": config["memory"]
                    }
                },
                "duration": f'{config["duration"]}s'
            }
        }
    else:
        name = f"cpu-chaos-{random.randint(1,100000)}"
        chaos_yaml = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {"name": name, "namespace": "sock-shop"},
            "spec": {
                "mode": "all",
                "selector": {
                    "namespaces": ["sock-shop"],
                    "pods": {
                        "sock-shop": config["pod"]
                    }
                },
                "stressors": {
                    "cpu": {
                        "workers": 1,
                        "load": config.get("load", 80)
                    }
                },
                "duration": f'{config["duration"]}s'
            }
        }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix=f"{name}-", dir=".", delete=False
    ) as chaos_file:
        yaml.dump(chaos_yaml, chaos_file)
        chaos_file_path = chaos_file.name
    try:
        subprocess.run(["kubectl", "apply", "-f", chaos_file_path], check=True)
    finally:
        os.unlink(chaos_file_path)

    resource_kind = "networkchaos" if config["resource"] == "network" else "stresschaos"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status = subprocess.run(
            ["kubectl", "get", resource_kind, name, "-n", "sock-shop", "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        resource = json.loads(status.stdout)
        conditions = resource.get("status", {}).get("conditions", [])
        if any(c.get("type") == "AllInjected" and c.get("status") == "True" for c in conditions):
            return name

        records = resource.get("status", {}).get("experiment", {}).get("containerRecords", [])
        failures = [
            event.get("message", "injection failed")
            for record in records
            for event in record.get("events", [])
            if event.get("type") == "Failed"
        ]
        if failures:
            delete_chaos(name, failed_injection=True)
            raise RuntimeError(f"Chaos Mesh failed to inject {name}: {failures[-1]}")
        time.sleep(1)

    subprocess.run(
        ["kubectl", "delete", resource_kind, name, "-n", "sock-shop", "--wait=false"],
        check=False,
    )
    raise TimeoutError(f"Chaos Mesh did not confirm injection for {name} within 30 seconds")

def delete_chaos(name, failed_injection=False):
    if name:
        kind = "networkchaos" if name.startswith("network-") else "stresschaos"
        target_pods = []
        if kind == "networkchaos":
            resource = subprocess.run(
                ["kubectl", "get", kind, name, "-n", "sock-shop", "-o", "json"],
                capture_output=True,
                text=True,
                check=False,
            )
            if resource.returncode == 0:
                target_pods = json.loads(resource.stdout).get("spec", {}).get(
                    "selector", {}).get("pods", {}).get("sock-shop", [])
        subprocess.run(
            ["kubectl", "delete", kind, name, "-n", "sock-shop", "--wait=false"],
            check=False,
        )
        if kind == "networkchaos":
            recovered = False
            status = subprocess.run(
                ["kubectl", "get", kind, name, "-n", "sock-shop", "-o", "json"],
                capture_output=True,
                text=True,
                check=False,
            )
            if status.returncode == 0:
                conditions = json.loads(status.stdout).get("status", {}).get("conditions", [])
                recovered = any(
                    condition.get("type") == "AllRecovered"
                    and condition.get("status") == "True"
                    for condition in conditions
                )
            if failed_injection or recovered:
                subprocess.run(
                    ["kubectl", "patch", kind, name, "-n", "sock-shop",
                     "--type=merge", "-p", '{"metadata":{"finalizers":[]}}'],
                    check=False,
                )
                remaining = subprocess.run(
                    ["kubectl", "get", "networkchaos", "-A", "-o", "json"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if remaining.returncode == 0:
                    resources = json.loads(remaining.stdout).get("items", [])
                    for pod in target_pods:
                        still_selected = any(
                            pod in item.get("spec", {}).get("selector", {})
                            .get("pods", {}).get("sock-shop", [])
                            for item in resources
                        )
                        if not still_selected:
                            subprocess.run(
                                ["kubectl", "delete", "podnetworkchaos", pod,
                                 "-n", "sock-shop", "--wait=false"],
                                check=False,
                            )
