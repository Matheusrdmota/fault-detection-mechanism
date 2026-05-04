import random
import subprocess
import yaml

def apply_chaos(config):

    if not config["leak_injected"]:
        return None

    name = ""
    chaos_yaml = {}
    if config["resource"] == "mem":
        name = f"memory-chaos-{random.randint(1,100000)}"
        chaos_yaml = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {"name": name},
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
            "metadata": {"name": name},
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

    with open("chaos.yaml", "w") as f:
        yaml.dump(chaos_yaml, f)

    subprocess.run(["kubectl", "apply", "-f", "chaos.yaml"])

    return name

def delete_chaos(name):
    if name:
        subprocess.run(["kubectl", "delete", "stresschaos", name])