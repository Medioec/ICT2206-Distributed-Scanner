import subprocess
from models.vm import VM
import time

# Functions related to k3s/kubernetes


def delete_node(vm: VM):
    node_name = vm.hostname.lower()
    subprocess.run(f"sudo kubectl delete node {node_name}".split(), capture_output=True)
    print(f"Deleted node {node_name} from k3s")


def build_docker_image():
    res = subprocess.run("git rev-parse --verify HEAD".split(), capture_output=True)
    hash = res.stdout.decode().strip()
    subprocess.run(f"docker image build image/. -t bunshinscanner:latest -t bunshinscanner:{hash}".split())
    subprocess.run("docker image tag bunshinscanner:latest ec18815/bunshinscanner:latest".split())
    subprocess.run("docker login".split())
    repo = input("Enter your docker repo (e.g. ec18815/bunshinscanner:latest): ")
    subprocess.run(f"docker push {repo}".split())


def get_all_pod_ips(vmcount: int):
    while True:
        res = subprocess.run("sudo kubectl get pods -o=jsonpath=\"{range .items[*]}{.status.podIP}{','}{end}\"", shell=True, capture_output=True)
        text = res.stdout.decode()
        text = text[:-1]
        ip_list = text.split(",")
        if len(ip_list) < vmcount:
            continue
        break
    for ip in ip_list:
        if ip == "":
            time.sleep(1)
            ip_list = get_all_pod_ips(vmcount)
            break
    return ip_list


def start_daemon_set(vmcount: int):
    print("Starting daemon set")
    print("Waiting for nodes to be ready, might take some time")
    while True:
        res = subprocess.run("sudo kubectl get nodes | grep Ready", shell=True, capture_output=True)
        nodes = res.stdout.decode().strip().split("\n")
        if len(nodes) == vmcount + 1:
            break
        time.sleep(2)
    time.sleep(2)
    subprocess.run("sudo kubectl apply -f daemonset.yaml".split())
    time.sleep(2)
    