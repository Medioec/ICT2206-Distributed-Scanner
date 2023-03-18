from time import sleep
import sys
import socket
import threading
import subprocess
import time
import datetime

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((socket.gethostname(), 54545))
    s.listen(5)
    while True:
        clientsocket, address = s.accept()
        thread = threading.Thread(target=thread_handle_connection, args=(clientsocket,))
        thread.start()


def thread_handle_connection(conn: socket.socket):
    strdata = conn.recv(4096).decode()
    strtoken, sep, rem = strdata.partition("\n")
    if strtoken == "command":
        ip, sep, rem = rem.partition("\n")
        run_command(ip, rem)
    elif strtoken == "wordlist":
        filename, sep, rem = rem.partition("\n")
        fd = open(filename, "w")
        fd.write(rem)
        while True:
            recv = conn.recv(4096).decode()
            if not recv:
                break
            fd.write(recv)
        fd.close()
    return


def run_command(ip: str, com: str):
    com = com.strip()
    comlist = com.split()
    try:
        print("Received " + com)
        run_and_transmit(ip, com)
    except Exception as e:
        print(str(e))
        print(f"Problem running command, attempting apt install {comlist[0]}")
        run_and_transmit(ip, f"apt install {comlist[0]} -y")
        try:
            run_and_transmit(ip, com)
        except Exception as e:
            print(str(e))
            print(f"Cannot run command {com}")
    return


def run_and_transmit(ip:str, com:str):
    ts = datetime.datetime.now().strftime("%d%m%Y, %H:%M:%S")
    first_token, sep, rem = com.partition(" ")
    proc = subprocess.run(["hostname"], capture_output=True)
    hostname = proc.stdout.decode().strip()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, 54545))
    s.send(f"output\n{first_token + hostname}.output\n\nTime: {ts} Command: {com}\n\n".encode())
    proc = subprocess.Popen(com, shell=True, stdout=subprocess.PIPE)
    for line in proc.stdout:
        print(line.decode().rstrip())
        s.send(line)
    status = proc.poll()
    if status != 0:
        s.close()
        raise Exception("Exit with non 0 status...")
    s.close()


if __name__ == "__main__":
    main()