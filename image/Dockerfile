# Filename Dockerfile
FROM kalilinux/kali-rolling
RUN mkdir /scripts
COPY ./main.py /scripts/main.py
RUN apt update && apt install python3 -y
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py|python3
