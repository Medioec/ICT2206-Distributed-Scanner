import subprocess
from models.vm import VM

def delete_node(vm: VM):
    node_name = vm.hostname.lower()
    subprocess.run(f"sudo kubectl delete node {node_name}".split(), capture_output=True)
    print(f"Deleted node {node_name} from k3s")
