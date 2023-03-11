import sys

from azure_management import *
import utility


def main(argv):
    display_notice()
    if not utility.check_powershell():
        utility.install_powershell()
    if not utility.check_k3s():
        utility.install_k3s()
    az = Azure()
    while True:
        display_main_options()
        usrinput = int(input())
        if usrinput == 1:
            new_scanner(az)
        elif usrinput == 2:
            delete_scanner(az)
        elif usrinput == 3:
            pass
        elif usrinput == 8:
            utility.generate_cloud_init("<agent ip here>")
        elif usrinput == 9:
            utility.install_k3s()


def new_scanner(az: Azure):
    number = display_scanner_options()
    az.create_vms(number)


def delete_scanner(az: Azure):
    az.delete_all_rg()


def display_main_options():
    print("""
            Scanning tool
            Please select an option to start:
            """)
    print("""
            [1] Create new scanner
            [2] Delete all scanners
            [3] Start scan
            [8] View cloud init template
            [9] Reinstall k3s
            """)


def display_scanner_options():
    print("""
            How many VMs to create? """, end="")
    num = int(input())
    return num


def display_notice():
    print("This tool requires root-level permissions and will automatically install required software. Proceed? (Y/N)")
    usrin = input()
    if usrin == "Y" or usrin == "y" or usrin == "":
        return
    else:
        sys.exit(0)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(0)
