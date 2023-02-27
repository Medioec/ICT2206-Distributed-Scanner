from dataclasses import dataclass
from models.resource_group import AZResourceGroup as azrg

@dataclass
class ScannerData(object):
    rg_list: list[azrg]
