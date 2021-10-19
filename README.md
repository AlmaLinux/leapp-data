# Migration guide

**NOTE: As this project is newly announced we HIGHLY recommend that you follow system administration best practices and make sure you have backups and/or snapshots of your system before you proceed. It is recommended to do a trial run in a sandbox to verify that migration worked as expected before you attempt to migrate any production system.**

This guide contains steps on how to upgrade CentOS 7 to RHEL8 derivatives such as AlmaLinux, CentOS, Oracle, Rocky.

To use this guide you need to install Vagrant and VirtualBox using the following
documentation:

* [Install VirtualBox](https://www.virtualbox.org/manual/ch02.html)
* [Install Vagrant](https://www.vagrantup.com/docs/installation)

* Clone this repo and cd into it
 ```
    git clone https://github.com/AlmaLinux/leapp-data.git
    cd leapp-data
 ```

* Start the Virtual Machine.
 ```
    vagrant up
 ```

* CentOS 7.9 is required to accomplish the upgrade. Login to VM, install the latest CentOS updates, and reboot.
 ```
    vagrant ssh
    sudo yum update -y
    sudo reboot
 ```

* After reboot login to VM again, download the leapp repo file, and install leapp.
 ```
    vagrant ssh
    sudo curl https://repo.almalinux.org/elevate/el7/elevate.repo -o /etc/yum.repos.d/elevate.repo
    sudo yum install leapp -y
 ```

* Copy leapp config files for the OS you want to migrate. Possible options are almalinux, centos, oraclelinux, rocky.
 ```
    sudo cp /vagrant/files/almalinux/* /etc/leapp/files/
 ```

* Start a preupgrade check. It will fail as the default CentOS 7 doesn't meet all requirements for migration. In the meanwhile, Leapp utility creates a special */var/log/leapp/leapp-report.txt* file that contains possible problems and recommended solutions. No rpm packages will be installed at this phase.
 ```
    sudo leapp preupgrade
 ```

   This summary report will help you get the picture of whether it is possible to continue the upgrade.

   In certain configurations, Leapp generates */var/log/leapp/answerfile* with true/false questions. Leapp utility requires answers to all these questions in order to proceed with the upgrade.

* Mentioned fixes from the */var/log/leapp/leapp-report.txt* file are mandatory, but you can also review the rest of them if needed.
```
   sudo rmmod pata_acpi
   echo PermitRootLogin yes | sudo tee -a /etc/ssh/sshd_config
   sudo leapp answer --section remove_pam_pkcs11_module_check.confirm=True
```

* Start an upgrade. After this process is completed you'll be offered to reboot the system.
 ```
    sudo leapp upgrade
    sudo reboot
```

* A new entry in GRUB called ELevate-Upgrade-Initramfs will appear. The system will be automatically booted into it.
   See how the update process goes in the VirtualBox console.

* After reboot, login to the system and check how the migration went. Verify that the current OS is the one you need.
 ```
   vagrant ssh
   cat /etc/redhat-release
   cat /etc/os-release
   rpm -qa | grep centos
   rpm -qf | grep el7
```
