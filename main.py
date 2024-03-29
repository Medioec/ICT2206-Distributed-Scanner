import sys
import os
from azure_management import *
from kubernetes_management import *
import utility
import socket
import threading
import datetime


def main(argv):
    display_notice()
    if not utility.check_powershell():
        utility.install_powershell()
    if not utility.check_k3s():
        utility.install_k3s()
    az = Azure()
    listener = threading.Thread(target=start_listener)
    listener.start()
    while True:
        display_main_options()
        usrinput = int(prompt_user_input())
        handle_selection(usrinput, az)


def display_main_options():
    print("""
            Scanning tool
            Make sure ports 6443 and 54545 on this device are reachable from the internet
            Please select an option to start:
            """)
    print("""
            [1] Create new scanner
            [2] Delete all scanners
            [3] Start scan
            [7] Build docker image
            [8] View cloud init template
            [9] Reinstall k3s
            """)


def handle_selection(usrinput:str, az:Azure):
    if usrinput == 1:
        new_scanner(az)
    elif usrinput == 2:
        delete_scanner(az)
    elif usrinput == 3:
        vmcount = az.get_number_of_vms()
        if vmcount == 0:
            print("No vms available")
            return
        cmd_example = "\ngobuster dir -u https://www.redapplepie.com -w #wordlist#list.txt\nhydra -l user -P #wordlist#list.txt www.redapplepie.com http-head /guac/\n"
        print(
            "Enter command to use for scanning\n"
            "Example syntax:\n"
            f"{cmd_example}\n"
            "'#' characters are necessary for additional processing by tool\n"
            "Wordlists have to be prepended with #wordlist#\n"
            "Replace fields with the required content\n\n"
        )
        cmd = input("Enter command for scanning: ")
        start_daemon_set(vmcount)
        ip_list = get_all_pod_ips(vmcount)
        parse_and_send_command(cmd, vmcount, ip_list)
    elif usrinput == 7:
        build_docker_image()
    elif usrinput == 8:
        cinit = utility.generate_cloud_init("<agent ip here>")
        print(cinit)
    elif usrinput == 9:
        utility.install_k3s()


def parse_and_send_command(cmd: str, num: int, ip_list: list[str]):
    filename = ""
    if "#wordlist#" in cmd:
        tokens = cmd.split()
        index = 0
        repindex = None
        for token in tokens:
            if "#wordlist#" in token:
                token = token.replace("#wordlist#", "")
                filename = token
                repindex = index
                break
            index += 1
        tokens[repindex] = tokens[repindex].replace("#wordlist#", "")
        cmd = " ".join(tokens)
    if filename != "":
        utility.split_wordlist(filename, num)
    for i in range(num):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip_list[i], 54545))
        if filename != "":
            fd = open(f"{filename}{i}", "r")
            filestr = "".join(fd.readlines())
            fd.close()
            textstr = f"wordlist\n{filename}\n" + filestr
            pbytes = bytes(textstr, "utf-8")
            s.sendall(pbytes)
            s.close()
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip_list[i], 54545))
        newcmd = f"command\n{utility.get_device_ip()}\n" + cmd
        pbytes = bytes(newcmd, "utf-8")
        s.sendall(pbytes)
        s.close()
    print("Check the new .output files created for the output. This script needs to remain running to receive output.")

def start_listener():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", 54545))
    s.listen(500)
    while True:
        clientsocket, address = s.accept()
        thread = threading.Thread(target=thread_listener, args=(clientsocket,))
        thread.start()



def thread_listener(conn: socket.socket):
    strdata = conn.recv(4096).decode()
    strtoken, sep, rem = strdata.partition("\n")
    if strtoken == "output":
        filename, sep, rem = rem.partition("\n")
        ts = datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        fd = open(filename, "a", encoding="utf-8")
        start_text = f"\nConnection received: {ts}\n"
        fd.write(start_text)
        fd.write(rem)
        while True:
            recv = conn.recv(4096).decode("utf-8", "ignore")
            if not recv:
                break
            fd.write(recv)
            fd.flush()
        ts = datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        end_text = f"\nConnection terminated: {ts}\n"
        fd.write(end_text)
        fd.close()
    return


def new_scanner(az: Azure):
    number = display_scanner_options()
    az.create_vms(number)


def delete_scanner(az: Azure):
    az.delete_all_rg()


def display_scanner_options():
    print("""
            How many VMs to create? """, end="")
    num = int(input())
    return num


def display_notice():
    print("This tool requires root-level permissions and will automatically install required software. Proceed? (Y/N) ", end="")
    usrin = input()
    if usrin == "Y" or usrin == "y" or usrin == "":
        return
    else:
        sys.exit(0)


def prompt_user_input():
    print("Selection: ", end="")
    return input()


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print("\n\nEnding...\n")
        os._exit(0)
