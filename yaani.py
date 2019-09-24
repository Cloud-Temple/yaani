#!/usr/bin/env python3

from __future__ import absolute_import

import argparse
import sys
import os
import yaml
try:
    import json
except ImportError:
    import simplejson as json

from lark import Lark, Transformer
import re

from jsonschema import validate
import pynetbox

# The name of the Environment variable where to find the path towards the
# configuration file
DEFAULT_ENV_CONFIG_FILE = "NETBOX_CONFIG_FILE"


class Transformer(Transformer):
    """The transformer to apply to tree of type System"""
    def __init__(self, data):
        self.data = data

    def expr(self, n):
        return n[0]

    def key_path(self, n):
        pointer = self.data
        for key in n:
            try:
                if key in list(pointer.keys()):
                    pointer = pointer[key]
                else:
                    sys.exit(
                        "Error: The key solving failed "
                        "in key_path '%s'" % (key_path)
                    )
            except AttributeError:
                return None

        return pointer

    def sub(self, n):
        if n[0] is None:
            return None
        data_str = str(n[0])
        pattern = str(n[1]).strip("\"").strip("\'")
        repl = str(n[2]).strip("\"").strip("\'")
        if len(n) > 3:
            return re.sub(
                pattern, repl, data_str,
                *list(map(lambda x: int(x), n[3:]))
            )
        return re.sub(pattern, repl, data_str)

    def default_key(self, n):
        if n[0] is None:
            return n[1]
        else:
            return n[0]


class InventoryBuilder:
    """Inventory Builder is the object that builds and return the inventory.

    Attributes:
        config_api (dict): The configuration of the api section
        config_data (dict): The configuration parsed from the configuration
                            file
        config_file (str): The path of thge configuration file
        host (str): The hostname if specified, None else
        imports (list): The list of import statements in the configuration file
        list_mode (bool): The value of --list option
        parser (Lark): The parser used to parse custom expressions.
    """

    def __init__(self, script_args, script_config):
        # Script args
        self.config_file = script_args.config_file
        self.host = script_args.host
        self.list_mode = script_args.list

        # Configuration file
        self.config_data = script_config['netbox']
        self.config_api = self.config_data['api']
        self.imports = self.config_data.get('import', None)
        # Expression resolutions objects
        grammar = """
            expr: sub
                | default_key
                | key_path

            default_key: expr "|" "default_key" "(" key_path ")"

            sub: expr "|" "sub" "(" STRING  "," STRING \
                                    ["," NUMBER  ["," NUMBER ]] ")"

            key_path: KEY_NAME ("." KEY_NAME)*
            KEY_NAME: /[_a-zA-Z0-9]+/

            %import common.ESCAPED_STRING   -> STRING
            %import common.SIGNED_NUMBER    -> NUMBER
            %import common.WS
            %ignore WS
        """

        self.parser = Lark(
            grammar, start="expr", parser='lalr'
        )

    def _init_inventory(self):
        return {'_meta': {'hostvars': {}}}

    def build_inventory(self):
        """Build and return the inventory dict.
        The inventory respects the following principles :
          - When the script is called with the single argument --list, the
            script must output to stdout a JSON-encoded hash or dictionary
            containing all of the groups to be managed. Each group’s value
            should be either a hash or dictionary containing a list of each
            host, any child groups, and potential group variables,
            or simply a list of hosts:

            {
                "group001": {
                    "hosts": ["host001", "host002"],
                    "vars": {
                        "var1": true
                    },
                    "children": ["group002"]
                },
                "group002": {
                    "hosts": ["host003","host004"],
                    "vars": {
                        "var2": 500
                    },
                    "children":[]
                }

            }

          - If any of the elements of a group are empty they may be omitted
            from the output.
          - When called with the argument --host <hostname> (where <hostname>
            is a host from above), the script must print either an empty JSON
            hash/dictionary, or a hash/dictionary of variables to make
            available to templates and playbooks. For example:

            {
                "VAR001": "VALUE",
                "VAR002": "VALUE",
            }
            -------------------------------------
          - FIXME: COMPLETE COMMENTS

        Returns:
            dict: The inventory
        """
        # If the list mode is specified, return a complete inventory
        if self.list_mode:
            inventory = self._init_inventory()

            # Check whether the import section exists.
            # If it exists, iterate over each statement, else, execute default
            # behaviour.
            if self.imports:
                # For each application, iterate over all inner object types
                for app_name, app_import in list(self.imports.items()):
                    for type_key, import_statement in app_import.items():
                        self._execute_import(
                            application=app_name,
                            import_type=type_key,
                            import_options=import_statement,
                            inventory=inventory
                        )
            else:
                # Execute default behaviour:
                #   -> get all devices and handle no grouping option
                self._execute_import(
                    application='dcim',
                    import_type='devices',
                    import_options={},
                    inventory=inventory
                )

            return inventory
        # If a host name is specified, return the inventory filled with only
        # its information
        elif self.host:
            inventory = self._init_inventory()

            # A host is considered to be a device. Check if devices import
            # options are set.
            device_import_options = (
                self.imports
                .get('dcim', {})
                .get('devices', {})
            )

            self._execute_import(
                application='dcim',
                import_type='devices',
                import_options=device_import_options,
                inventory=inventory
            )

            return inventory['_meta']['hostvars'].get(self.host, {})
        #  If none of the list or host options is set, return an empty dict
        else:
            return {}

    def _execute_import(self, application, import_type,
                        import_options, inventory):
        """Fetch requested entities in Netbox.

        Args:
            application (str): The name of the netbox application.
                example: dcim, virtualization, etc.
            import_type (str): The type of objects to fetch from Netbox.
            import_options (str): The complementary arguments to refine search.
            inventory (dict): The inventory in which the information must be
                added.
        """
        # Fetch the list of entities from Netbox
        netbox_hosts_list = self._get_elements_list(
            application, import_type,
            filters=import_options.get('filters', None),
            specific_host=self.host
        )

        # If the netbox hosts list fetching was successful, add the elements to
        # the inventory.
        if netbox_hosts_list:
            for host in netbox_hosts_list:
                # Compute an id for the given host data
                element_name = self._get_identifier(dict(host), import_type)
                # Add the element to the propper group(s)
                self._add_element_to_inventory(
                    element_name, dict(host), inventory, import_type,
                    import_options.get('group_by', None),
                    import_options.get('group_prefix', None),
                    import_options.get('host_vars', None)
                )

    def _load_element_vars(self, element_name, host,
                           inventory, host_vars=None):
        # If there is no required host var to load, end here.
        if host_vars:
            host_data = {}
            # Iterate over every key value pairs in host_vars required in
            # config file
            for key, value in host_vars.items():
                # Set the name of the key
                if value == 'ALL':
                    host_data[key] = host
                else:
                    try:
                        host_data[key] = self._resolve_expression(
                            key_path=value,
                            data=host
                        )
                    except KeyError:
                        sys.exit("Error: Key '%s' not found" % value)

            # Add the loaded variables in the inventory under the proper
            # section (name of the host)
            inventory['_meta']['hostvars'].update(
                {element_name: host_data}
            )

    def _add_element_to_inventory(self, element_name, host, inventory,
                                  obj_type, group_by=None, group_prefix=None,
                                  host_vars=None):
        """Insert the given element in the propper groups.

        Args:
            element_name (str): The name of the element
            host (dict): The actual data of the element
            inventory (dict): The inventory in which the element must be
                inserted.
            obj_type (str): The type of the element
            group_by (list, optional): The list of group ot create and to add
                the element to.
            group_prefix (str, optional): An optional prefix to add in front
                of group names that will be created.
        """
        # If the group_by option is specified, insert the element in the
        # propper groups.
        if group_by:
            # Iterate over every groups
            for group in group_by:
                # Check that the specified group points towards an actual value
                if (
                    self._resolve_expression(key_path=group, data=host)
                    is not None
                ):
                    # The 'tags' field is a list, a second iteration must be
                    # performed at a deeper level
                    if group == 'tags':
                        # Iterate over every tag
                        for tag in host.get(group):
                            group_name = tag
                            # Add the optional prefix
                            if group_prefix is not None:
                                group_name = group_prefix + group_name
                            # Insert the element in the propper group
                            self._add_element_to_group(
                                element_name=element_name,
                                group_name=group_name,
                                inventory=inventory
                            )
                    else:
                        # Check that the specified group points towards an
                        # actual value
                        group_name = self._resolve_expression(
                            key_path=group, data=host
                        )
                        # Add the optional prefix
                        if group_prefix:
                            group_name = group_prefix + group_name
                        # Insert the element in the propper group
                        self._add_element_to_group(
                            element_name=element_name,
                            group_name=group_name,
                            inventory=inventory
                        )
        # Anyway, add the host to its main type group ( evices, racks, etc.)
        # and to the group 'all'
        self._add_element_to_group(
            element_name=element_name, group_name=obj_type, inventory=inventory
        )
        self._add_element_to_group(
            element_name=element_name, group_name='all', inventory=inventory
        )

        # Load the host vars in the inventory
        self._load_element_vars(
            element_name, host,
            inventory,
            host_vars
        )

    def _get_elements_list(self, application, object_type,
                           filters=None, specific_host=None):
        """Retrieves a list of element from netbox API.

        Returns:
            A list of all elements from netbox API.

        Args:
            application (str): The name of the netbox application
            object_type (str): The type of object to import
            filters (dict, optional): The filters to pass on to pynetbox calls
            specific_host (str, optional): The name of a specific host which
                host vars must be returned alone.
        """
        nb = pynetbox.api(**self.config_api)

        app_obj = getattr(nb, application)
        endpoint = getattr(app_obj, object_type)

        # specific host handling
        if specific_host is not None:
            result = []
            h = endpoint.get(name=specific_host)
            if h:
                result.append(h)
        elif filters is not None:
            result = endpoint.filter(**filters)
        else:
            result = endpoint.all()

        return result

    def _add_element_to_group(self, element_name, group_name, inventory):
        self._initialize_group(group_name=group_name, inventory=inventory)
        if element_name not in inventory.get(group_name).get('hosts'):
            inventory[group_name]['hosts'].append(element_name)

    def _get_identifier(self, host, obj_type):
        """Return an identifier for the given host.

        Args:
            host (str): The name of the host
            obj_type (str): The type of the object

        Returns:
            str: The computed id
        """
        # Get the 'name' field value of the specified host
        r = host.get('name')
        # If the 'name' field is empty, compute the id :
        #   <object type>_<id in netbox db>
        if r is None or r == "":
            r = "%s_%s" % (obj_type, host.get('id'))
        return r

    def _initialize_group(self, group_name, inventory):
        """
        Args:
            group_name (str): The group to be initialized
            inventory (dict): The inventory including the group

        Returns:
            The updated inventory
        """
        # Initialize the group in the inventory
        inventory.setdefault(group_name, {})
        # Initialize the host field of the group
        inventory[group_name].setdefault('hosts', [])
        return inventory

    def _resolve_expression(self, key_path, data):
        """Resolve the given key path to a value.

        Args:
            key_path (str): The path toward the key
            data (dict): The actual host data dict that holds
                the target value.

        Returns:
            The target value
        """
        t = Transformer(data=data)
        return t.transform(self.parser.parse(key_path))


def parse_cli_args(script_args):
    """Declare and configure script argument parser

    Args:
            script_args (list): The list of script arguments

    Returns:
            obj: The parsed arguments in an object. See argparse documention
                 (https://docs.python.org/3.7/library/argparse.html)
                 for more information.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config-file',
        default=os.getenv(DEFAULT_ENV_CONFIG_FILE, "netbox.yml"),
        help="""Path for script's configuration file. If None is specified,
                default value is %s environment variable or netbox.yml in the
                current dir.""" % DEFAULT_ENV_CONFIG_FILE
    )
    parser.add_argument(
        '--list', action='store_true', default=False,
        help="""Print the entire inventory with hostvars respecting
                the Ansible dynamic inventory syntax."""
    )
    parser.add_argument(
        '--host', action='store', default=None,
        help="""Print specific host vars as Ansible dynamic
                inventory syntax."""
    )

    # Parse script arguments and return the result
    return parser.parse_args(script_args)


def validate_configuration(configuration):
    """Validate the configuration structure. If no error is found, nothing
    happens.

    Args:
            configuration (dict): The parsed configuration
    """

    config_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://example.com/product.schema.json",
        "title": "Configuration file",
        "description": "The configuration file of the dynamic inventory",
        "type": "object",
        "properties": {
            "netbox": {
                "type": "object",
                "description": "The base key of the configuration file",
                "properties": {
                    "api": {
                        "type": "object",
                        "description": (
                            "The section holding information used "
                            "to connect to netbox api"
                        ),
                        "additionalProperties": False,
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The url of netbox api"
                            },
                            "token": {
                                "type": "string",
                                "description": "The netbox token to use"
                            },
                            "private_key": {
                                "type": "string",
                                "description": "The private key"
                            },
                            "private_key_file": {
                                "type": "string",
                                "description": "The private key file"
                            },
                            "ssl_verify": {
                                "type": "boolean",
                                "description": (
                                    "Specify SSL verification behavior"
                                )
                            }
                        },
                        "required": ["url"],
                        "allOf": [
                            {
                                "not": {
                                    "type": "object",
                                    "required": [
                                        "private_key",
                                        "private_key_file"
                                    ]
                                }
                            }
                        ]
                    },
                    "import": {
                        "type": "object",
                        "description": "The netbox application",
                        "minProperties": 1,
                        "additionalProperties": False,
                        "patternProperties": {
                            "^": {
                                "type": "object",
                                "description": "The import section",
                                "minProperties": 1,
                                "additionalProperties": False,
                                "patternProperties": {
                                    "^": {
                                        "type": "object",
                                        "minProperties": 1,
                                        "additionalProperties": False,
                                        "properties": {
                                            "group_by": {
                                                "type": "array",
                                                "minItems": 1,
                                                "items": {
                                                    "type": "string"
                                                }
                                            },
                                            "group_prefix": {
                                                "type": "string",
                                            },
                                            "filters": {
                                                "type": "object",
                                                "minProperties": 1,
                                                "description": (
                                                    ""
                                                )
                                            },
                                            "host_vars": {
                                                "type": "object",
                                                "minProperties": 1
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "required": ["api"]
            }
        },
        "required": ["netbox"]
    }

    return validate(instance=configuration, schema=config_schema)


def load_config_file(config_file_path):
    """ Load the configuration file and returns its parsed content.

    Args:
            config_file_path (str): The path towards the configuration file
    """
    try:
        with open(config_file_path, 'r') as file:
            parsed_config = yaml.safe_load(file)
    except IOError as io_error:
        # Handle file level exception
        sys.exit("Error: Cannot open configuration file.\n%s" % io_error)
    except yaml.YAMLError as yaml_error:
        # Handle Yaml level exceptions
        sys.exit("Error: Unable to parse configuration file: %s" %
                 yaml_error)

    # If syntax of configuration file is valid, nothing happens
    # Beware, syntax can be valid while semantic is not
    validate_configuration(parsed_config)

    return parsed_config


def dump_json_inventory(inventory):
    """Dumps the given inventory in json

    Args:
            inventory (dict): The inventory
    """
    print(json.dumps(inventory))


def main():
    # Parse cli args
    args = parse_cli_args(sys.argv[1:])
    # Parse the configuration file
    configuration = load_config_file(args.config_file)

    # Build the inventory
    builder = InventoryBuilder(args, configuration)
    # Print the JSON formatted inventory dict
    dump_json_inventory(builder.build_inventory())

if __name__ == '__main__':
    main()
