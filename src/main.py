from src.detector.linear_reg import detection_init
import random
import src.config.kubernetes.k8s_config as k8s_config
import src.external.chaos_manager.chaos_manager as chaos_manager
import time

memory_sizes = ["350MB", "500MB"]
cpu_loads = [80]
durations = [120, 180, 240]

def run_random_experiments(n=10):
    for i in range(n):
        print(f"\n========== EXPERIMENTO {i+1} ==========")
        
        resource = random.choice(["cpu", "mem"])

        chaos_config = generate_random_fault(resource)
        print("Config:", chaos_config)
        chaos_name = chaos_manager.apply_chaos(chaos_config)
        time.sleep(chaos_config["duration"] + 25)

        summary = detection_init(resource, chaos_config, chaos_name)
        
        print("Resultado salvo:", summary)

def generate_random_fault(resource):
    leak = random.random() <= 0.9
    pod_selected = []
    injections = random.randint(1, 2)

    pods = k8s_config.get_pods()
    pods_label = k8s_config.get_pods_label()

    pod_selected.extend(random.sample(pods, injections))

    config = {
        "pod": pod_selected,
        "pod_label": [pods_label[pods.index(p)] for p in pod_selected],
        "duration": random.choice(durations),
        "leak_injected": leak,
        "resource": resource
    }

    if resource == "cpu":
        config["cpu"] = random.choice(cpu_loads)
    else:
        config["memory"] = random.choice(memory_sizes)

    
    print(resource)
    
    return config

run_random_experiments()