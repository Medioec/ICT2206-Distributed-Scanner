import sys

from azure_management import *


def main(argv):
    az = Azure()
    while True:
        display_main_options()
        usrinput = int(input())
        if usrinput == 1:
            new_scanner(az)
        elif usrinput == 2:
            delete_scanner(az)


def new_scanner(az: Azure):
    number = display_scanner_options()
    az.create_vms(number)


def delete_scanner(az: Azure):
    az.delete_rg()


def display_main_options():
    print("""
            Scanning tool
            Please select an option to start:
            """)
    print("""
            [1] Create new scanner
            [2] Delete all scanners
            """)


def display_scanner_options():
    print("""
            How many VMs to create?
            """)
    num = int(input())
    return num


def install_powershell():
    print("Installing powershell")
    subprocess.run("wget https://github.com/PowerShell/PowerShell/releases/download/v7.3.2/powershell_7.3.2-1.deb_amd64.deb".split())
    subprocess.run("sudo apt install ./powershell-lts_7.3.2-1.deb_amd64.deb".split())
    res = subprocess.run("pwsh -Command echo \"Powershell installed successfully\"", capture_output=True)
    teststr = res.stdout.decode().strip()
    if teststr != "Powershell installed successfully":
        print("Unable to install powershell, please install manually")


def install_k3s():
    print("Installing k3s")
    subprocess.run("curl -sfL https://get.k3s.io | sudo sh -")


def get_k3s_token():
    fd = open("/var/lib/rancher/k3s/server/node-token", "r")
    token = fd.read()
    return token


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(0)
