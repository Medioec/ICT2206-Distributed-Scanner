import os
import subprocess
import base64
from requests import get

def get_k3s_token() -> str:
        res = subprocess.run("sudo cat /var/lib/rancher/k3s/server/node-token".split(), capture_output=True)
        token = res.stdout.decode().strip()
        return token


def get_device_ip() -> str:
    return get("https://api.ipify.org").content.decode()


def check_powershell() -> bool:
    try:
        subprocess.run("pwsh -Command echo ''".split(), capture_output=True)
        return True
    except:
        return False


def install_powershell():
    print("Installing powershell")
    subprocess.run("wget https://github.com/PowerShell/PowerShell/releases/download/v7.3.2/powershell_7.3.2-1.deb_amd64.deb".split())
    subprocess.run("sudo apt install ./powershell_7.3.2-1.deb_amd64.deb".split())
    try:
        check_powershell()
    except:
        print("Unable to install powershell, please install manually")
    finally:
        os.remove("powershell_7.3.2-1.deb_amd64.deb")


def check_k3s() -> bool:
    try:
        subprocess.run("sudo k3s".split(), capture_output=True)
        return True
    except:
        return False


def install_k3s():
    print("Installing k3s")
    subprocess.run("curl -sfL https://get.k3s.io -o k3sinstall.sh".split())
    subprocess.run(f"sudo sh k3sinstall.sh --node-external-ip {get_device_ip()} --flannel-backend wireguard-native --flannel-external-ip".split())
    os.remove("k3sinstall.sh")


def generate_cloud_init(agent_ip:str):
    master_server_ip = get_device_ip()
    token = get_k3s_token()
    cloud_init_string = (
        "\n#cloud-config\n"
        "runcmd:\n"
        "  - apt update && apt upgrade -y\n"
        f"  - curl -sfL https://get.k3s.io | K3S_URL=https://{master_server_ip}:6443 K3S_TOKEN={token} INSTALL_K3S_EXEC=\"--node-external-ip {agent_ip} --node-label type=scanner\" sh -s -\n"
    )
    return cloud_init_string


def encode_cloud_init(plaintext:str) -> str:
    return base64.b64encode(plaintext.encode("utf-8")).decode("latin-1")


def split_wordlist(filename: str, num: int):
    word = open(filename, "r")
    num_lines = sum(1 for line in word)
    word.seek(0)
    rem = num_lines%num
    each = num_lines//num
    for i in range(num):
        fd = open(filename + str(i), "w")
        if rem > 0:
            additional = 1
        else:
            additional = 0
        
        for j in range(each + additional):
            line = word.readline()
            fd.write(line)
        rem -= 1
        fd.close()
        