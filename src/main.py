from src.detector.linear_reg import detection_init
import random
import argparse
import json
import src.config.kubernetes.k8s_config as k8s_config
import src.external.chaos_manager.chaos_manager as chaos_manager
import src.external.prometheus.prometheus_client as prom_cli
import subprocess
import threading
import time

memory_sizes = ["350MB", "500MB"]
cpu_loads = [80]
durations = [120, 180]
network_loss_rates = ["10"]
network_congestion_rates = ["64kbps"]
# Exercise the same delay detector at multiple fault strengths. Callers can
# override a level with --latency when they need a specific experiment.
network_delay_latencies = ["100ms", "200ms", "500ms", "1000ms"]
network_long_response_time_latencies = ["100ms", "200ms", "500ms", "1000ms"]
HTTP_SERVICE_NAMES = {
    "carts", "catalogue", "front-end", "orders", "payment",
    "queue-master", "shipping", "user",
}
HTTP_ENDPOINT_PORTS = {80, 8079}


def _start_sock_shop_traffic(targets):
    """Measure HTTP batches concurrently against the selected target pods."""
    source_pods = [
        name for name, _label in k8s_config.get_pods_with_labels()
        if name.startswith("catalogue-")
    ]
    if not source_pods:
        raise RuntimeError("No catalogue pod found to generate in-cluster traffic")
    source_pod = source_pods[0]
    stop_event = threading.Event()
    latency_samples = []
    samples_lock = threading.Lock()

    def measure_batch(target):
        command = [
            "kubectl", "exec", "-n", "sock-shop", source_pod, "--", "sh", "-c",
            f"ok=0; i=0; while [ $i -lt 4 ]; do if wget -q -T 3 -O /dev/null http://{target['target_ip']}:{target['target_port']}/; then ok=$((ok+1)); fi; i=$((i+1)); done; echo $ok",
        ]
        started_at = time.time()
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
        successful = int(result.stdout.strip().splitlines()[-1])
        return started_at, target["pod"], time.time() - started_at, successful / 4.0

    def generate_traffic(target):
        while not stop_event.is_set():
            try:
                sample = measure_batch(target)
                with samples_lock:
                    latency_samples.append(sample)
            except (subprocess.SubprocessError, OSError):
                stop_event.wait(1)

    workers = []
    try:
        for target in targets:
            latency_samples.append(measure_batch(target))
        for target in targets:
            worker = threading.Thread(target=generate_traffic, args=(target,), daemon=True)
            workers.append(worker)
            worker.start()
    except (subprocess.SubprocessError, OSError) as error:
        stop_event.set()
        for worker in workers:
            worker.join(timeout=2)
        raise RuntimeError(
            "Could not generate HTTP traffic for all selected target pods"
        ) from error
    return stop_event, workers, latency_samples

def _run_network_trial(index, chaos_config):
    stop_traffic = None
    workers = []
    chaos_name = None
    try:
        print(f"\n========== EXPERIMENTO {index + 1} ==========")
        print("Config:", chaos_config)
        stop_traffic, workers, latency_samples = _start_sock_shop_traffic(
            chaos_config["targets"]
        )
        time.sleep(70)
        network_training_data = prom_cli.query_prometheus(
            "regression", "network", 0
        )
        fault_start_time = time.time()
        chaos_name = chaos_manager.apply_chaos(chaos_config)
        time.sleep(chaos_config["duration"] + 25)
        summary = detection_init(
            "network",
            chaos_config,
            chaos_name,
            latency_samples=latency_samples,
            fault_start_time=fault_start_time,
            target_pod=chaos_config["pod"],
            fault_type=chaos_config["fault_type"],
            network_training_data=network_training_data,
        )
        print(f"Experimento {index + 1} salvo:", summary)
        return summary
    finally:
        if stop_traffic is not None:
            stop_traffic.set()
        for worker in workers:
            worker.join(timeout=2)
        chaos_manager.delete_chaos(chaos_name)


def run_random_experiments(
    n=10,
    duration_override=None,
    force_injection=False,
    force_control=False,
    target_pod_override=None,
    fault_type_override=None,
    latency_override=None,
):
    previously_selected = set()
    fault_types = ("packet_loss", "congestion", "delay", "long_response_time")
    for index in range(n):
        trial_fault_type = fault_type_override or fault_types[index % len(fault_types)]
        chaos_config = generate_random_fault(
            "network", previously_selected,
            target_pod_override=target_pod_override,
            fault_type_override=trial_fault_type,
            latency_override=latency_override,
        )
        if duration_override is not None:
            chaos_config["duration"] = duration_override
        if force_injection:
            chaos_config["leak_injected"] = True
        if force_control:
            chaos_config["leak_injected"] = False

        _run_network_trial(index, chaos_config)
        previously_selected.update(chaos_config["pod"])


def run_cpu_experiments(
    n=1, duration_override=60, force_injection=False, force_control=False,
    target_pod_override=None,
):
    """Run controlled CPU StressChaos trials and evaluate Prometheus CPU metrics."""
    pods = k8s_config.get_pods()
    candidates = [pod for pod in pods if not any(
        token in pod.lower() for token in ("prometheus", "chaos", "istio")
    )]
    if not candidates:
        raise RuntimeError("No eligible Running pods found in sock-shop for CPU experiments")
    if target_pod_override:
        candidates = [pod for pod in candidates if pod == target_pod_override]
        if not candidates:
            raise RuntimeError(f"Requested target {target_pod_override} is not a Running pod")
    for index in range(n):
        pod_count = 1 if target_pod_override else random.randint(1, min(2, len(candidates)))
        selected_pods = (
            [candidates[0]] if target_pod_override
            else random.sample(candidates, k=pod_count)
        )
        inject_fault = force_injection or (
            not force_control and random.random() <= 0.9
        )
        chaos_config = {
            "pod": selected_pods, "duration": duration_override, "leak_injected": inject_fault,
            "resource": "cpu", "load": 80, "fault_type": "cpu_hog",
        }
        print(f"\n========== CPU HOG {index + 1}/{n} ==========")
        print("Config:", chaos_config)
        chaos_name = chaos_manager.apply_chaos(chaos_config)
        try:
            time.sleep(duration_override + 25)
            summary = detection_init("cpu", chaos_config, chaos_name)
        finally:
            chaos_manager.delete_chaos(chaos_name)
        print("Resultado salvo:", summary)


def run_memory_experiments(
    n=1, duration_override=None, force_injection=False, force_control=False,
    target_pod_override=None,
):
    """Run memory StressChaos trials and evaluate Prometheus memory metrics."""
    pods = k8s_config.get_pods()
    candidates = [pod for pod in pods if not any(
        token in pod.lower() for token in ("prometheus", "chaos", "istio")
    )]
    if not candidates:
        raise RuntimeError("No eligible Running pods found in sock-shop for memory experiments")
    if target_pod_override:
        candidates = [pod for pod in candidates if pod == target_pod_override]
        if not candidates:
            raise RuntimeError(f"Requested target {target_pod_override} is not a Running pod")

    for index in range(n):
        pod_count = 1 if target_pod_override else random.randint(1, min(2, len(candidates)))
        selected_pods = (
            [candidates[0]] if target_pod_override
            else random.sample(candidates, k=pod_count)
        )
        inject_fault = force_injection or (
            not force_control and random.random() <= 0.9
        )
        chaos_config = {
            "pod": selected_pods,
            "duration": duration_override or random.choice(durations),
            "leak_injected": inject_fault,
            "resource": "mem",
            "memory": random.choice(memory_sizes),
            "fault_type": "memory_leak",
        }
        print(f"\n========== MEMORY LEAK {index + 1}/{n} ==========")
        print("Config:", chaos_config)
        chaos_name = chaos_manager.apply_chaos(chaos_config)
        try:
            time.sleep(chaos_config["duration"] + 25)
            summary = detection_init("mem", chaos_config, chaos_name)
        finally:
            chaos_manager.delete_chaos(chaos_name)
        print("Resultado salvo:", summary)

def generate_random_fault(
    resource, previously_selected=None, excluded_targets=None, target_pod_override=None,
    fault_type_override=None, latency_override=None,
):
    fault_injected = random.random() <= 0.9
    trial_fault_type = fault_type_override or random.choice(
        ["packet_loss", "congestion", "delay"]
    )
    pod_selected = []
    injections = random.randint(1, 2)
    network_targets = []

    pod_inventory = k8s_config.get_pods_with_labels()
    pods = [name for name, _label in pod_inventory]
    pods_label = [label for _name, label in pod_inventory]

    if resource == "network":
        # Choose from live HTTP-serving application pods, then direct the
        # measured workload to that exact pod so the injection is observable.
        endpoints_data = json.loads(subprocess.run(
            ["kubectl", "get", "endpoints", "-n", "sock-shop", "-o", "json"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout).get("items", [])
        candidate_endpoints = {}
        for endpoint in endpoints_data:
            service_name = endpoint.get("metadata", {}).get("name")
            if service_name not in HTTP_SERVICE_NAMES:
                continue
            for subset in endpoint.get("subsets", []):
                for address in subset.get("addresses", []):
                    pod_name = address.get("targetRef", {}).get("name")
                    if not pod_name or pod_name.startswith("catalogue-"):
                        continue
                    for port in subset.get("ports", []):
                        if int(port.get("port", 0)) not in HTTP_ENDPOINT_PORTS:
                            continue
                        candidate_endpoints.setdefault(
                            pod_name, (address["ip"], int(port["port"]))
                        )
        source_pods = [pod for pod in pods if pod.startswith("catalogue-")]
        if not source_pods:
            raise RuntimeError("No catalogue pod found to generate in-cluster traffic")
        reachable_candidates = []
        for candidate, (ip, port) in candidate_endpoints.items():
            try:
                probe = subprocess.run(
                    ["kubectl", "exec", "-n", "sock-shop", source_pods[0], "--", "sh", "-c",
                     f"wget -q -T 3 -O /dev/null http://{ip}:{port}/"],
                    capture_output=True, text=True, timeout=5,
                )
                if probe.returncode == 0:
                    reachable_candidates.append((candidate, ip, port))
            except (subprocess.SubprocessError, OSError):
                # Unresponsive candidates are skipped; they must not abort target selection.
                continue
        if not reachable_candidates:
            raise RuntimeError("No active Sock Shop Service endpoint responded to HTTP from catalogue")
        target_count = 1
        if target_pod_override:
            selected = [row for row in reachable_candidates if row[0] == target_pod_override]
            if not selected:
                raise RuntimeError(
                    f"Requested target {target_pod_override} is not an active HTTP endpoint"
                )
            selected_targets = selected
        else:
            excluded = excluded_targets or set()
            viable_candidates = [row for row in reachable_candidates if row[0] not in excluded]
            if not viable_candidates:
                raise RuntimeError(
                    "NetworkChaos injection failed for every reachable HTTP pod in this experiment"
                )
            unselected_candidates = [
                row for row in viable_candidates if row[0] not in (previously_selected or set())
            ]
            preferred_candidates = unselected_candidates
            if len(preferred_candidates) < target_count:
                preferred_candidates = viable_candidates
            if len(preferred_candidates) < target_count:
                raise RuntimeError(
                    f"{trial_fault_type} requires {target_count} distinct active HTTP endpoints"
                )
            selected_targets = random.sample(preferred_candidates, k=target_count)
        for selected_pod, target_ip, target_port in selected_targets:
            pod_selected.append(selected_pod)
            network_targets.append({
                "pod": selected_pod,
                "target_ip": target_ip,
                "target_port": target_port,
            })
    else:
        pod_selected.extend(random.sample(pods, injections))

    config = {
        "pod": pod_selected,
        "pod_label": [pods_label[pods.index(p)] for p in pod_selected],
        "targets": network_targets if resource == "network" else None,
        "target_ip": network_targets[0]["target_ip"] if network_targets else None,
        "target_port": network_targets[0]["target_port"] if network_targets else None,
        "duration": random.choice(durations),
        "leak_injected": fault_injected,
        "resource": resource,
        "fault_type": trial_fault_type,
    }

    if resource == "cpu":
        config["cpu"] = random.choice(cpu_loads)
    elif resource == "mem":
        config["memory"] = random.choice(memory_sizes)
    elif resource == "network":
        if config["fault_type"] == "packet_loss":
            config["loss"] = random.choice(network_loss_rates)
        elif config["fault_type"] == "congestion":
            config["rate"] = random.choice(network_congestion_rates)
        elif config["fault_type"] == "delay":
            config["latency"] = latency_override or random.choice(network_delay_latencies)
        elif config["fault_type"] == "long_response_time":
            config["latency"] = latency_override or random.choice(network_long_response_time_latencies)
    
    return config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run controlled fault-detection experiments")
    parser.add_argument("--experiments", type=int, default=10)
    parser.add_argument("--resource", choices=("network", "cpu", "mem"), default="network")
    parser.add_argument("--duration", type=int, choices=(60, 120, 180, 240))
    parser.add_argument("--target-pod", help="Restrict a trial to a specific pod")
    parser.add_argument("--fault-type", choices=("packet_loss", "congestion", "delay", "long_response_time"),
                        help="Force packet-loss, congestion, network-delay, or long-response-time experiments")
    parser.add_argument(
        "--latency",
        help="Set injected delay for delay/long_response_time trials (for example 200ms or 750ms)",
    )
    fault_group = parser.add_mutually_exclusive_group()
    fault_group.add_argument("--force-injection", action="store_true")
    fault_group.add_argument("--force-control", action="store_true")
    args = parser.parse_args()
    if args.resource == "cpu":
        run_cpu_experiments(
            n=args.experiments,
            duration_override=args.duration or 60,
            force_injection=args.force_injection,
            force_control=args.force_control,
            target_pod_override=args.target_pod,
        )
    elif args.resource == "mem":
        run_memory_experiments(
            n=args.experiments,
            duration_override=args.duration,
            force_injection=args.force_injection,
            force_control=args.force_control,
            target_pod_override=args.target_pod,
        )
    else:
        run_random_experiments(
        n=args.experiments,
        duration_override=args.duration,
        force_injection=args.force_injection,
        force_control=args.force_control,
        target_pod_override=args.target_pod,
        fault_type_override=args.fault_type,
            latency_override=args.latency,
        )
