# Yet Another Ansible Netbox Inventory

Yaani stands for Yet Another Ansible Netbox Inventory. It is a dynamic inventory script sourcing information from Netbox to make it available in Ansible.

## Requirements

All the requirements are listed in the requirements.txt file.

## Installation

In order to install the dependencies, simply run the following command in the root folder:
```
make install
```
This requires to have the make package installed.

In case it is not installed, run :
```
pip install -r requirements.txt
```

## Tests

A test suite is available in the tests forlder. To run the test suite, you must have pytest installed.
Run the following command if you make installed :
```
make test
```
 If it is not the case, run :
```
pytest
```

## Principles

### General

The dynamic inventory script can fetch different kind of elements from Netbox to provide a lot of information to Ansible playbooks. By default, Yaani retrieves all devices from Netbox and group them in a group 'devices', but using the configuration file allows extracting more objects such as racks, sites etc.

### Configuration File

The dynamic inventory script is configured via a YAML configuration file. Its path can be given to the script in several ways by order of precedence :
- With -c option
- With the NETBOX_CONFIG_FILE environment variable
By default, if none of these are provided to the script, it will try to load a netbox.yml file in the current directory.

The configuration file consists in two sections: api & import.

The api section is mandatory. It contains api_url and optionnaly api_token.

The import section is optionnal. If not present, the script prints the list all devices and add them to group 'devices'. It then return the inventory without loading any hostvar.
If present, it must contain at least one subsection called import statement. There can be more than one import statement, each must be named after the type of element to be retrieved from Netbox (devices, racks, sites, etc.).

Each import statement contains several key/value pairs which are detailed later in the following sections :
- filter
- group_by
- host_vars

### Group by

Devices or other elements can be grouped using values in Netbox. In an import statement, the 'group_by' keyword can be used to create groups.

```
Example

...
import:
  devices:
    group_by:
      - key1
      - key2
...
```

The values passed to group_by can be Netbox keys or key paths (explained later).

Tags can be used for grouping feature as well as any key found in a Netbox object.

*CAUTION*: Please pay attention to the fact that a same value found in two differents keys in Netbox will point to the same group and with mixed elements in the group.

### Group prefix

If the group_by statement is used, it is possible to prefix every group name created for an import statement with the given prefix. It allows one to avoid
having conflicting group names for elements of differents types.

### Filter

The filter statement allows one to filter elements requested to Netbox API. It narrows the search by the mean of a filter appended to the API URL.

```
Example

import:
  devices:
	filter: "role_id=1&name=X"
```

### Host vars

Hostvars for hosts can be loaded from Netbox using the 'host_vars' statement in the configuration file.

#### Example
```
...
import:
  devices:
    host_vars:
      # Load the value of primary_ip and make it accessible in the 'host_ip' variable.
      host_ip: primary_ip
...
```

Key path can also be specified instead of simple Netbox key name.

A special 'ALL' keyword is provided in order to load the entire piece of information from Netbox.

In case a host has no name in Netbox, it is named after its Netbox ID, prefixed by its object type.

#### Example
```

...
import:
  devices:
    host_vars:
	  # make all information from Netbox available in the variable 'main'
	  main: ALL
	  ...
```

### Key path

When specifying a key from Netbox in group_by or host_vars sections, a simple key name can be used. The value of that key in Netbox is used.
It is also possible to specify a key path to point to keys inside nested dictionnaries. The key path is a string containing key names separated by dots.

In order to apply transformations to the value obtained after key path resolution, some additional builtin filters may
be applied.

The supported builtin are the following :
  - sub: it is used in the same way as the python function 'sub' from the re module. Indeed, it is executed by
    this very function.
  - key_path: Takes one argument as a key path which value must be returned if the preceding expression value is None.

#### Example
To point to key 'label' inside the dict a the 'status' key, you can use the following key path :
```
status.label
```

To point to an ip address, you can use :
```
primary_ip.address
```
The resulting value will be the primary IP of the current host, suffixed with CIDR notation SNM.

If you want to remove the subnet mask, you can use the 'sub' filter which shall remove the given regex in the way
re.sub python function does (it is actually executed with this function).
```
primary_ip.address | sub("/[0-9]+", "")
```

## Usage

```
usage: yaani.py [-h] [-c CONFIG_FILE] [--list] [--host HOST]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Path for script's configuration file. If None is
                        specified, default value is NETBOX_CONFIG_FILE
                        environment variable or netbox.yml in the current dir.
  --list                Print the entire inventory with hostvars respecting
                        the Ansible dynamic inventory syntax.
  --host HOST           Print specific host vars as Ansible dynamic inventory
                        syntax.
```

```
./yaani.py -c netbox.yml --list
```

## Example

I want to get every device that matches a specific role. I want them grouped by tags and rack names, and I want to load their primary IP as hostvars under the name primary_ip.
I also want all the racks to be loaded with all possible information under the name rack_main.

```
netbox:
  api:
    api_url: "https://netbox.private.lan/api/"
    # api_token: "<Netbox token>"

  import:
    devices:
      filter: "role_id=<id of the role in Netbox>"
      group_by:
        - rack.name
        - tags
      host_vars:
        primary_ip: primary_ip.address

    racks:
      host_vars:
        rack_main: ALL
```

## Authors

* **Antoine Delannoy** - *Initial work* - [a-delannoy](https://github.com/a-delannoy)

## Acknowledgments

* Inspired from https://github.com/AAbouZaid/netbox-as-ansible-inventory project (https://github.com/AAbouZaid)
