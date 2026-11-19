import json
import subprocess


NAMESPACE = "sock-shop"


def get_pods_with_labels():
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", NAMESPACE, "-o", "json"],
        capture_output=True,
        text=True,
        check=True
    )
    items = json.loads(result.stdout).get("items", [])

    pods = []
    for item in items:
        if item.get("status", {}).get("phase") != "Running":
            continue

        metadata = item.get("metadata", {})
        name = metadata.get("name")
        labels = metadata.get("labels", {})
        app_label = (
            labels.get("app.kubernetes.io/name")
            or labels.get("app")
            or (name.rsplit("-", 2)[0] if name else None)
        )
        if name:
            pods.append((name, app_label or name))

    if not pods:
        raise RuntimeError(f"No Running pods found in namespace {NAMESPACE}")

    return sorted(pods)


def get_pods():
    return [name for name, _label in get_pods_with_labels()]


def get_pods_label():
    return [label for _name, label in get_pods_with_labels()]
