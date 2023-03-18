from time import sleep
import socket
import threading
import subprocess

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
        run_command(rem)
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


def run_command(com: str):
    com = com.strip()
    try:
        print("Received" + com)
        subprocess.run(com.split())
    except:
        print(f"Problem running command, attempting apt install {com[0]}")
        subprocess.run(f"apt install {com[0]}".split())
        try:
            subprocess.run(com.split())
        except:
            print(f"Cannot run command {com}")
    return


if __name__ == "__main__":
    main()