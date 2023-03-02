from dataclasses import dataclass

@dataclass
class VM(object):
    username: str
    password: str
    public_ip: str
    hostname: str
