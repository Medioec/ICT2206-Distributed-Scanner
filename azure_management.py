import os
import subprocess
import uuid

from azure.identity import AzurePowerShellCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkSecurityGroup, SecurityRule, SecurityRuleProtocol

import jsonpickle as jspk

from models.resource_group import AZResourceGroup as azrg
from models.scanner_data import ScannerData
from models.vm import VM

SCANNERDATAFILE = "scannerdata.json"
NAME_PREFIX = "BunshinScanner"
VMUSERNAME = "bunshin"

class Azure:
    rg_list:list[azrg] = None
    subscription_id:str = None

    def __init__(self):
        self.rg_list = []
        self.credential, self.subscription_id = self.login_to_azure_ps()
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)
        self.load_info_from_file()

    def create_rg(self, datetime_string:str, n:int):
        rg_result = self.resource_client.resource_groups.create_or_update(f"{NAME_PREFIX}-{datetime_string}-rg",{"location": "southeastasia"})
        rgobj = azrg(rg_result.name, rg_result.location, datetime_string, list())
        self.rg_list.append(rgobj)
        print(f"Resource group {rg_result.name} created in {rg_result.location} region")
        self.save_info_to_file()
        return rg_result.name

    def delete_rg(self):
        print("Deleting, this will take a long time")
        for rg in self.rg_list:
            poller = self.resource_client.resource_groups.begin_delete(rg.name)
            result = poller.result()
            print(f"Resource group {rg.name} in {rg.location} has been deleted")
        self.rg_list.clear()
        os.remove(SCANNERDATAFILE)
        print("All resource groups have been deleted")
        return

    def create_vms(self, dt_str:str, n:int):
        print("Creating VMs, this may take a while")
        new_rg_name = self.create_rg(dt_str, n)
        prefix = f"{NAME_PREFIX}-{dt_str}-"
        VNET_NAME = prefix + "vn"
        SUBNET_NAME = prefix + "sn"
        IP_NAME = prefix + "ip"
        IP_CONFIG_NAME = prefix + "ipconfig"
        NIC_NAME = prefix + "nic"
        SG_NAME = prefix + "sg"

        selected_rg: azrg = None
        for rg in self.rg_list:
            if rg.name == new_rg_name:
                selected_rg = rg
        if selected_rg == None:
            print("Error, no rg selected")
            exit(1)

        # Obtain the management object for networks
        network_client = NetworkManagementClient(self.credential, self.subscription_id)

        # Provision the security group
        nsg = NetworkSecurityGroup(location = rg.location)
        nsg.security_rules = [
            SecurityRule(
                name='AllowAllInboundTraffic',
                protocol=SecurityRuleProtocol.asterisk,
                source_address_prefix='*',
                source_port_range='*',
                destination_address_prefix='*',
                destination_port_range='*',
                access='Allow',
                direction='Inbound',
                priority=100
            )
        ]
        async_security_group = network_client.network_security_groups.begin_create_or_update(
            rg.name,
            SG_NAME,
            parameters = nsg
        )

        security_group = async_security_group.result()
        print(f"Provisioned security group {security_group.name} allowing all traffic")

        # Provision the virtual network and wait for completion
        poller = network_client.virtual_networks.begin_create_or_update(
            rg.name,
            VNET_NAME,
            {
                "location": rg.location,
                "address_space": {"address_prefixes": ["10.0.0.0/16"]},
            },
        )

        vnet_result = poller.result()

        print(
            f"Provisioned virtual network {vnet_result.name} with address prefixes {vnet_result.address_space.address_prefixes}"
        )

        # Step 3: Provision the subnet and wait for completion
        poller = network_client.subnets.begin_create_or_update(
            rg.name,
            VNET_NAME,
            SUBNET_NAME,
            {"address_prefix": "10.0.0.0/24"},
        )
        subnet_result = poller.result()

        print(
            f"Provisioned virtual subnet {subnet_result.name} with address prefix {subnet_result.address_prefix}"
        )

        for i in range(n):
            # Step 4: Provision an IP address and wait for completion
            poller = network_client.public_ip_addresses.begin_create_or_update(
                rg.name,
                IP_NAME + str(i),
                {
                    "location": rg.location,
                    "sku": {"name": "Standard"},
                    "public_ip_allocation_method": "Static",
                    "public_ip_address_version": "IPV4",
                },
            )

            ip_address_result = poller.result()

            print(
                f"Provisioned public IP address {ip_address_result.name} with address {ip_address_result.ip_address}"
            )

            # Step 5: Provision the network interface client
            poller = network_client.network_interfaces.begin_create_or_update(
                rg.name,
                NIC_NAME + str(i),
                {
                    "location": rg.location,
                    "network_security_group": {
                        "name": SG_NAME,
                        "id": security_group.id,
                        "location": rg.location
                    },
                    "ip_configurations": [
                        {
                            "name": IP_CONFIG_NAME,
                            "subnet": {"id": subnet_result.id},
                            "public_ip_address": {"id": ip_address_result.id},
                        }
                    ],
                },
            )

            nic_result = poller.result()

            print(f"Provisioned network interface client {nic_result.name}")

            # Step 6: Provision the virtual machine

            # Obtain the management object for virtual machines
            compute_client = ComputeManagementClient(self.credential, self.subscription_id)

            VM_NAME = prefix + "vm" + str(i)
            USERNAME = VMUSERNAME
            temp = str(uuid.uuid4())
            PASSWORD = temp

            print(
                f"Provisioning virtual machine {VM_NAME}, this operation might take a while"
            )

            # Provision the VM specifying only minimal arguments, which defaults
            # to an Ubuntu 18.04 VM on a Standard DS1 v2 plan with a public IP address
            # and a default virtual network/subnet.

            poller = compute_client.virtual_machines.begin_create_or_update(
                rg.name,
                VM_NAME,
                {
                    "location": rg.location,
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
                        "admin_username": USERNAME,
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

            vm_result = poller.result()

            print(f"Provisioned virtual machine {vm_result.name}")
            rg.vm_list.append(VM(USERNAME, PASSWORD, ip_address_result.ip_address))
        self.save_info_to_file()
        return

    @staticmethod
    def login_to_azure_ps() -> AzurePowerShellCredential:
        id = Azure.get_subscription_id()
        if id != "":
            creds = AzurePowerShellCredential()
            return creds, id
        print("Checking for installation of azure powershell")
        subprocess.run(["powershell", "-Command", """
                        if (-not(Get-Module -ListAvailable -Name Az.Accounts)) {
                            Write-Host "Installing azure powershell, this will take some time"
                            Install-Module -Name Az -Scope CurrentUser -Repository PSGallery -Force
                        }
                        """])
        print("Logging in to azure, enter you credentials in the new window")
        subprocess.run(["powershell", "-Command", "Connect-AzAccount"])
        id = Azure.get_subscription_id()
        if id != "":
            creds = AzurePowerShellCredential()
            return creds, id
        else:
            print("Unable to load credentials")
            exit(1)

    @staticmethod
    def get_subscription_id():
        res = subprocess.run(["powershell", "-Command", "(Get-AzContext).Subscription.id"], capture_output=True)
        id = res.stdout.decode().strip()
        return id

    def save_info_to_file(self):
        sdobj = ScannerData(self.rg_list)
        json = jspk.encode(sdobj, indent=6)
        fd = open(SCANNERDATAFILE, "w")
        fd.write(json)
        fd.close()
        return

    def load_info_from_file(self):
        sdobj: ScannerData
        if not os.path.exists(SCANNERDATAFILE):
            self.rg_list = []
            return
        fd = open(SCANNERDATAFILE, "r")
        json = fd.read()
        fd.close()
        sdobj = jspk.decode(json)
        self.rg_list = sdobj.rgs
        return