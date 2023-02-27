import sys

from azure_management import *


def main(argv):
    display_notice()
    check_powershell()
    az = Azure()
    while True:
        display_main_options()
        usrinput = int(input())
        if usrinput == 1:
            new_scanner(az)
        elif usrinput == 2:
            delete_scanner(az)
        elif usrinput == 8:
            az.generate_cloud_init_string()
        elif usrinput == 9:
            install_k3s()


def new_scanner(az: Azure):
    number = display_scanner_options()
    az.generate_cloud_init_string()
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
            [8] Generate cloud init
            [9] Install k3s
            """)


def display_scanner_options():
    print("""
            How many VMs to create?
            """)
    num = int(input())
    return num


def display_notice():
    print("This tool will automatically install required software. Proceed? (Y/N)")
    usrin = input()
    if usrin == "Y" or usrin == "y" or usrin == "":
        return
    else:
        sys.exit(0)


def check_powershell():
    try:
        subprocess.run("pwsh -Command echo ''".split())
    except:
        install_powershell()


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


def install_k3s():
    print("Installing k3s")
    subprocess.run("curl -sfL https://get.k3s.io -o k3sinstall.sh".split())
    subprocess.run("sudo sh k3sinstall.sh".split())
    os.remove("k3sinstall.sh")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(0)
