from dataclasses import dataclass
from models.vm import VM

@dataclass
class AZResourceGroup(object):
    name: str
    location: str
    creation_date: str
    vm_list:list[VM]
