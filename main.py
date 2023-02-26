import sys
import subprocess
from datetime import datetime

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

def new_scanner(az:Azure):
    number = display_scanner_options()
    time = datetime.now()
    dt_str = time.strftime("%Y%m%d-%H%M%S")
    az.create_vms(dt_str, number)

def delete_scanner(az:Azure):
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

if __name__ == "__main__":
    main(sys.argv)