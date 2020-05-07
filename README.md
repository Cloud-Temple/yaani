# Yaani - Yet another Ansible Netbox inventory

Yaani is an Ansible dynamic inventory script designed to source its data from the Netbox API. A configuration file written in YAML is used to describe the desired shape of the inventory. It can be used along with Ansible when running a playbook, for example :
```
Ansible-playbook -i yaani.py my-playbook.yml
```

It can also be used on a standalone basis, calling its cli options manually.
```
usage: yaani.py [-h] [-c CONFIG_FILE] [--list] [--host HOST]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Path for script's configuration file. If None is
                        specified, default value is YAANI_CONFIG_FILE
                        environment variable or netbox.yml in the current dir.
  --list                Print the entire inventory with hostvars respecting
                        the Ansible dynamic inventory syntax.
  --host HOST           Return an empty inventory.
```

## Getting started

### Installation

In order to install Yaani, you can clone the repository:
```
git clone https://github.com/Cloud-Temple/yaani.git
```

and install its dependencies:
```
make install
```

In case make is not installed, simply run:
```pip install -r requirements.txt```

### Requirements

All the requirements are provided in the requirements.txt file in a pip freeze fashion.

### First step

Fore more information about how to use dynamic inventory plugin, please visit https://github.com/Cloud-Temple/yaani/wiki/Home-Page