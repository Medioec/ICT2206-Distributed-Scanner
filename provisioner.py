import uuid
from datetime import datetime

from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkSecurityGroup, SecurityRule

from models.resource_group import AZResourceGroup as Azrg

NAME_PREFIX = "BunshinScanner"
VMUSERNAME = "bunshin"


class Provisioner:
    resource_client: ResourceManagementClient
    compute_client: ComputeManagementClient
    network_client: NetworkManagementClient
    rg: Azrg  # Each provisioner only provisions resources for its own rg
    datetime_str: str

    def __init__(self, credential, subscription_id: str, rg: Azrg = None):
        if rg is None:
            time = datetime.now()
            dt_str = time.strftime("%Y%m%d-%H%M%S")
            self.datetime_str = dt_str
        else:
            delimited = rg.name.split("-")
            dt_str = delimited[1] + "-" + delimited[2]
            self.datetime_str = dt_str
        prefix = f"{NAME_PREFIX}-{dt_str}-"
        self.RG_NAME = prefix + "rg"
        self.VNET_NAME = prefix + "vn"
        self.SUBNET_NAME = prefix + "sn"
        self.IP_NAME = prefix + "ip"
        self.IP_CONFIG_NAME = prefix + "ipconfig"
        self.NIC_NAME = prefix + "nic"
        self.SG_NAME = prefix + "sg"

        self.rg = rg
        self.credential = credential
        self.subscription_id = subscription_id
        self.resource_client = ResourceManagementClient(credential, subscription_id)
        self.compute_client = ComputeManagementClient(credential, subscription_id)
        self.network_client = NetworkManagementClient(credential, subscription_id)

    def provision_resource_group(self, location: str):
        if self.rg is not None:
            # Provisioner can only have 1 rg
            print("Provisioner should only have 1 rg (fix code pls)")
            return
        resource_group = self.resource_client.resource_groups.create_or_update(self.RG_NAME, {"location": location})
        self.rg = Azrg(resource_group.name, resource_group.location, self.datetime_str, list())
        return resource_group

    def delete_resource_group(self):
        async_rg_delete = self.resource_client.resource_groups.begin_delete(self.rg.name)
        return async_rg_delete

    def provision_security_group(self):
        nsg = NetworkSecurityGroup(location=self.rg.location)
        nsg.security_rules = [
            SecurityRule(
                name='AllowAllInboundTraffic',
                protocol='*',
                source_address_prefix='*',
                source_port_range='*',
                destination_address_prefix='*',
                destination_port_range='*',
                access='Allow',
                direction='Inbound',
                priority=100
            )
        ]
        async_security_group = self.network_client.network_security_groups.begin_create_or_update(
            self.rg.name,
            self.SG_NAME,
            parameters=nsg
        )
        return async_security_group

    def provision_virtual_network(self):
        async_virtual_network = self.network_client.virtual_networks.begin_create_or_update(
            self.rg.name,
            self.VNET_NAME,
            {
                "location": self.rg.location,
                "address_space": {"address_prefixes": ["10.0.0.0/16"]},
            },
        )
        return async_virtual_network

    def provision_subnet(self):
        async_subnet = self.network_client.subnets.begin_create_or_update(
            self.rg.name,
            self.VNET_NAME,
            self.SUBNET_NAME,
            {"address_prefix": "10.0.0.0/24"},
        )
        return async_subnet

    def provision_vm(self, number, sg_result, sn_result):
        async_ip = self.network_client.public_ip_addresses.begin_create_or_update(
            self.rg.name,
            self.IP_NAME + str(number),
            {
                "location": self.rg.location,
                "sku": {"name": "Standard"},
                "public_ip_allocation_method": "Static",
                "public_ip_address_version": "IPV4",
            },
        )
        ip_result = async_ip.result()
        async_nic = self.network_client.network_interfaces.begin_create_or_update(
                self.rg.name,
                self.NIC_NAME + str(number),
                {
                    "location": self.rg.location,
                    "network_security_group": {
                        "name": self.SG_NAME,
                        "id": sg_result.id,
                        "location": self.rg.location
                    },
                    "ip_configurations": [
                        {
                            "name": self.IP_CONFIG_NAME,
                            "subnet": {"id": sn_result.id},
                            "public_ip_address": {"id": ip_result.id},
                        }
                    ],
                },
            )
        nic_result = async_nic.result()

        prefix = f"{NAME_PREFIX}-{self.datetime_str}-"
        VM_NAME = prefix + "vm" + str(number)
        PASSWORD = str(uuid.uuid4())

        async_vm = self.compute_client.virtual_machines.begin_create_or_update(
            self.rg.name,
            VM_NAME,
            {
                "location": self.rg.location,
                "storage_profile": {
                    "image_reference": {
                        "publisher": "Canonical",
                        "offer": "0001-com-ubuntu-server-focal",
                        "sku": "20_04-lts-gen2",
                        "version": "latest",
                    }
                },
                "hardware_profile": {"vm_size": "Standard_B1s"},
                "os_profile": {
                    "computer_name": VM_NAME,
                    "admin_username": VMUSERNAME,
                    "admin_password": PASSWORD,
                },
                "network_profile": {
                    "network_interfaces": [
                        {
                            "id": nic_result.id,
                        }
                    ]
                },
            },
        )
        vm_result = async_vm.result()
        return vm_result, VMUSERNAME, PASSWORD, ip_result.ip_address
