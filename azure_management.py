import sys
import os
import subprocess
import concurrent.futures
import base64
from requests import get

from azure.identity import AzurePowerShellCredential

import jsonpickle as jspk

from models.resource_group import AZResourceGroup as Azrg
from models.scanner_data import ScannerData
from models.vm import VM
from provisioner import Provisioner

SCANNERDATAFILE = "scannerdata.json"


class Azure:
    rg_list: list[Azrg] = None
    subscription_id: str = None
    cloud_init_string: str = ""

    def __init__(self):
        self.rg_list = []
        self.credential, self.subscription_id = self.login_to_azure_ps()
        self.load_info_from_file()

    def create_rg(self, prov: Provisioner):
        rg_result = prov.provision_resource_group("southeastasia")
        rg = Azrg(prov.rg.name, prov.rg.location, prov.rg.creation_date, prov.rg.vm_list)
        self.rg_list.append(rg)
        print(f"Resource group {rg_result.name} created in {rg_result.location} region")
        self.save_info_to_file()
        return rg

    def delete_rg(self):
        print("Deleting, this will take a long time")
        templist = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            for rg in self.rg_list:
                prov = Provisioner(self.credential, self.subscription_id, rg)
                poller = prov.delete_resource_group()
                future = executor.submit(poller.result)
                templist.append((future, rg.name, rg.location))
                print("Deleting " + rg.name)
            for future, name, location in templist:
                result = future.result()
                print(f"Deleted resource group {name} in {location} region")
        if os.path.exists(SCANNERDATAFILE):
            os.remove(SCANNERDATAFILE)
        self.rg_list.clear()
        print("All resource groups have been deleted")
        return

    def create_vms(self, n: int):
        print("Creating VMs, this may take a while")
        prov = Provisioner(self.credential, self.subscription_id)
        rg = self.create_rg(prov)
        async_security_group = prov.provision_security_group()
        vn_result = prov.provision_virtual_network().result()
        print(
            f"Provisioned virtual network {vn_result.name} with address prefixes {vn_result.address_space.address_prefixes}"
        )
        sn_result = prov.provision_subnet().result()
        print(
            f"Provisioned virtual subnet {sn_result.name} with address prefix {sn_result.address_prefix}"
        )
        sg_result = async_security_group.result()
        print(f"Provisioned security group {sg_result.name} allowing all traffic")
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            templist = []
            for i in range(n):
                future = executor.submit(prov.provision_vm, i, sg_result, sn_result, self.cloud_init_string)
                templist.append(future)
                print("Provisioning vm" + str(i))
            for i in range(n):
                vm_result, username, password, ip = templist[i].result()
                # vm_result, username, password, ip = prov.provision_vm(i, sg_result, sn_result)
                rg.vm_list.append(VM(username, password, ip))
                print(f"Provisioned virtual machine {vm_result.name} with ip address {ip}")
                self.save_info_to_file()
        return

    @staticmethod
    def login_to_azure_ps():
        id = Azure.get_subscription_id()
        if id != "":
            creds = AzurePowerShellCredential()
            return creds, id
        print("Checking for installation of azure powershell")
        subprocess.run(["pwsh", "-Command", """
                        if (-not(Get-Module -ListAvailable -Name Az.Accounts)) {
                            Write-Host "Installing azure powershell, this will take some time"
                            Install-Module -Name Az -Scope CurrentUser -Repository PSGallery -Force
                        }
                        """])
        print("Logging in to azure, enter you credentials in the new window")
        # for headless linux: pwsh -Command Connect-AzAccount -UseDeviceAuthentication
        subprocess.run(["pwsh", "-Command", "Connect-AzAccount"])
        id = Azure.get_subscription_id()
        if id != "":
            creds = AzurePowerShellCredential()
            return creds, id
        else:
            print("Unable to load credentials")
            sys.exit(1)

    @staticmethod
    def get_subscription_id():
        res = subprocess.run(["pwsh", "-Command", "(Get-AzContext).Subscription.id"], capture_output=True)
        id = res.stdout.decode().strip()
        return id

    def save_info_to_file(self):
        sdobj = ScannerData(self.rg_list)
        json = jspk.encode(sdobj, indent=4)
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
        self.rg_list = sdobj.rg_list
        return


    def generate_cloud_init_string(self):
        ip = get("https://api.ipify.org").content.decode()
        token = Azure.get_k3s_token()
        print(f"{ip}, {token}")
        cloud_init_string = (
            "#cloud-config\n"
            "runcmd:\n"
            "  - apt update && apt upgrade -y\n"
            f"  - curl -sfL https://get.k3s.io | K3S_URL=https://{ip}:6443 K3S_TOKEN={token} sh -"
        )
        print(cloud_init_string)
        cloud_init_string = base64.b64encode(cloud_init_string.encode("utf-8")).decode("latin-1")
        self.cloud_init_string = cloud_init_string


    @staticmethod
    def get_k3s_token():
        res = subprocess.run("sudo cat /var/lib/rancher/k3s/server/node-token".split(), capture_output=True)
        token = res.stdout.decode().strip()
        return token
