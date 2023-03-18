# Filename Dockerfile
# Dockerfile for building docker image. Kubernetes will pull the image from dockerhub.
FROM kalilinux/kali-rolling
RUN mkdir /scripts
RUN apt update && apt install python3 -y
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py|python3
COPY ./main.py /scripts/main.py
