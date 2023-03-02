import sys
import os
import subprocess
import concurrent.futures

from azure.identity import AzurePowerShellCredential
from azure.core.exceptions import ResourceNotFoundError

import jsonpickle as jspk

from models.resource_group import AZResourceGroup as Azrg
from models.scanner_data import ScannerData
from models.vm import VM
from provisioner import Provisioner
from kubernetes_management import delete_node

SCANNERDATAFILE = "scannerdata.json"


class Azure:
    rg_list: list[Azrg] = None
    subscription_id: str = None

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

    def delete_all_rg(self):
        print("Deleting, this will take a long time")
        templist = []
        try:
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
        except ResourceNotFoundError as e:
            print("Resource group not found, skipping...")
        for rg in self.rg_list:
            for vm in rg.vm_list:
                delete_node(vm)
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
                future = executor.submit(prov.provision_vm, i, sg_result, sn_result)
                templist.append(future)
                print("Provisioning vm" + str(i))
            for i in range(n):
                vm_result, username, password, ip = templist[i].result()
                # vm_result, username, password, ip = prov.provision_vm(i, sg_result, sn_result)
                rg.vm_list.append(VM(username, password, ip, vm_result.name))
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
        print("Logging in to azure...")
        # for headless linux: pwsh -Command Connect-AzAccount -UseDeviceAuthentication
        subprocess.run(["pwsh", "-Command", "Connect-AzAccount", "-UseDeviceAuthentication"])
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

