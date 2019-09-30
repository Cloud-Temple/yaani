#!/usr/bin/env python3
from __future__ import absolute_import

from functools import reduce
import logging
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


class Namespace:
    def __init__(self, name, key, vars_dict={}):
        self.vars = vars_dict.copy()
        self.name = name
        self.key = key

    def get_key(self):
        return self.key

    def __str__(self):
        return self.name + " namespace"

    def __dict__(self):
        return self.vars

    def __getitem__(self, key):
        return self.vars[key]

    def __setitem__(self, key, value):
        self.vars[key] = value

    def keys(self):
        return self.vars.keys()

    def items(self):
        return self.vars.items()


class StackTransformer(Transformer):
    def __init__(self, vars_definition, api_connector, import_namespace,
                 sub_import_namespace):
        self.api_connector = api_connector
        self.vars_definition = vars_definition
        self.import_namespace = import_namespace
        self.sub_import_namespace = sub_import_namespace

    def _import_var(self, parent_namespace, loading_var):
        # Access var configuration
        try:
            var_configuration = self.vars_definition[loading_var]
        except KeyError:
            sys.exit(
                "Bad key %s in sub-import section. Variable not defined in "
                "sub_import.vars section." % loading_var
            )

        # Access netbox location of wanted object
        app = getattr(self.api_connector, var_configuration['application'])
        endpoint = getattr(app, var_configuration['type'])

        # Resolve filter args from "device_id": id to "device_id": 123
        filter_args = {}
        for k, v in var_configuration['filter'].items():
            try:
                filter_args[k] = parent_namespace[v]
            except KeyError:
                sys.exit(
                    "The key given as a filter value '%s' does not exist." % v
                )

        # fetch sub elements from netbox
        elements = endpoint.filter(**filter_args)

        # Set the name of the key that will be used for index
        index_key_name = var_configuration['index']

        ret = {}
        for e in elements:
            # Resolve the actual index value
            key = getattr(e, index_key_name)
            if key in list(ret.keys()):
                sys.exit(
                    "The key '%s', specified as an index key, is resolved to "
                    "non unique values." % key
                )
            ret[key] = dict(e)

        return ret

    def stack(self, n):
        return n[0]

    def nested_path(self, n):
        sub_pointer = [self.sub_import_namespace]
        parent_ns = self.import_namespace

        for path in n:
            l = []
            for v in sub_pointer:
                if parent_ns is None:
                    parent_ns = v
                v[str(path)] = self._import_var(
                    parent_namespace=parent_ns,
                    loading_var=str(path)
                )
                l += list(v[str(path)].values())
            parent_ns = None
            sub_pointer = l

        return self.sub_import_namespace


class KeyPathTransformer(Transformer):
    """The transformer to apply to tree of type System"""
    def __init__(self, build_ns=Namespace("build", "b"),
                 import_ns=Namespace("import", "i"),
                 sub_import_ns=Namespace("sub-import", "s")):
        self.namespaces = {}
        self.namespaces[build_ns.get_key()] = build_ns
        self.namespaces[import_ns.get_key()] = import_ns
        self.namespaces[sub_import_ns.get_key()] = sub_import_ns

    def expr(self, n):
        return n[0]

    def key_path(self, n):
        # Select the proper namespace to use
        try:
            pointer = self.namespaces[str(n[0])]
        except KeyError:
            # If the namespace was not found, use import namespace by default
            pointer = self.namespaces["i"]
        # Remove the namespace indication
        keys_list = n[1:]
        for key in keys_list:
            try:
                if key in list(pointer.keys()):
                    pointer = pointer[key]
                elif key == 'ALL' and key is keys_list[-1]:
                    return pointer
                else:
                    sys.exit(
                        "Error: The key solving failed "
                        "in key_path '%s'" % (keys_list)
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

    def namespace(self, n):
        if len(n):
            return str(n[0])
        return None


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

        # Create the api connector
        self.nb = pynetbox.api(**self.config_api)

        # Expression resolutions objects
        key_path_grammar = """
            expr: sub
                | default_key
                | key_path

            default_key: expr "|" "default_key" "(" key_path ")"

            sub: expr "|" "sub" "(" STRING  "," STRING \
                                    ["," NUMBER  ["," NUMBER ]] ")"

            key_path: namespace KEY_NAME ("." KEY_NAME)*
            namespace: ("<" NAMESPACES ">")?
            KEY_NAME: /\\w+/
            NAMESPACES: /[isb]/

            %import common.ESCAPED_STRING   -> STRING
            %import common.SIGNED_NUMBER    -> NUMBER
            %import common.WS
            %ignore WS
        """

        stack_grammar = """
            stack: nested_path

            nested_path: VAR ("." VAR)*
            VAR: /\\w+/
        """

        self.key_path_parser = Lark(
            key_path_grammar, start="expr", parser='lalr'
        )

        self.stack_parser = Lark(
            stack_grammar, start="stack",
        )

    def _init_inventory(self):
        return {'_meta': {'hostvars': {}}}

    def build_inventory(self):
        """Build and return the inventory dict.

        Returns:
            dict: The inventory
        """
        # Check if both mode are deactivated
        if not self.list_mode and not self.host:
            return {}

        inventory = self._init_inventory()

        if self.list_mode:

            if self.imports:
                # Check whether the import section exists.
                iterator = self.imports
            else:
                # Set the default behaviour args
                iterator = {
                    "dcim": {
                        "devices": {}
                    }
                }

            # For each application, iterate over all inner object types
            for app_name, app_import in list(self.imports.items()):
                for type_key, import_statement in app_import.items():
                    self._execute_import(
                        application=app_name,
                        import_type=type_key,
                        import_options=import_statement,
                        inventory=inventory
                    )

            return inventory
        else:
            # The host mode is on:
            #   If a host name is specified, return the inventory filled with
            #   only its information.
            #   A host is considered to be a device. Check if devices import
            #   options are set.
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
        # Access vars in config
        filters = import_options.get("filters", None)
        group_by = import_options.get('group_by', None)
        group_prefix = import_options.get('group_prefix', None)
        host_vars_section = import_options.get('host_vars', None)
        sub_import = import_options.get('sub_import', None)

        # Fetch the list of entities from Netbox
        netbox_hosts_list = self._get_elements_list(
            application,
            import_type,
            filters=filters,
            specific_host=self.host
        )

        # If the netbox hosts list fetching was successful, add the elements to
        # the inventory.
        for host in netbox_hosts_list:
            # Compute an id for the given host data
            element_index = self._get_identifier(dict(host), import_type)
            # Add the element to the propper group(s)
            self._add_element_to_inventory(
                element_index=element_index,
                host_dict=dict(host),
                inventory=inventory,
                obj_type=import_type,
                group_by=group_by,
                group_prefix=group_prefix,
                host_vars=host_vars_section,
                sub_import=sub_import
            )

    def _load_element_vars(self, element_name, host, inventory,
                           host_vars=None,
                           build_ns=None,
                           import_ns=None,
                           sub_import_ns=None):
        # If there is no required host var to load, do nothing.
        if host_vars:
            # Iterate over every key value pairs in host_vars required in
            # config file
            for d in host_vars:
                for key, value in d.items():
                    try:
                        build_ns[key] = self._resolve_expression(
                            key_path=value,
                            build_ns=build_ns,
                            import_ns=import_ns,
                            sub_import_ns=sub_import_ns
                        )
                    except KeyError:
                        sys.exit("Error: Key '%s' not found" % value)

            # Add the loaded variables in the inventory under the proper
            # section (name of the host)
            inventory['_meta']['hostvars'].update(
                {element_name: dict(build_ns)}
            )

    def _execute_sub_import(self, sub_import, import_namespace,
                            sub_import_namespace):
        # Extract stack string
        stack_string = sub_import['stack']

        # Extract vars definition
        vars_definition = {}
        for i in sub_import['vars']:
            vars_definition.update(i)

        t = StackTransformer(
            api_connector=self.nb,
            vars_definition=vars_definition,
            import_namespace=import_namespace,
            sub_import_namespace=sub_import_namespace
        )
        return t.transform(self.stack_parser.parse(stack_string))

    def _add_element_to_inventory(self, element_index, host_dict, inventory,
                                  obj_type, group_by=None, group_prefix=None,
                                  host_vars=None, sub_import=None):
        """Insert the given element in the propper groups.

        Args:
            element_index (str): The name of the element
            host_dict (dict): The actual data of the element
            inventory (dict): The inventory in which the element must be
                inserted.
            obj_type (str): The type of the element
            group_by (list, optional): The list of group ot create and to add
                the element to.
            group_prefix (str, optional): An optional prefix to add in front
                of group names that will be created.
        """
        # Declare namespaces
        build_namespace = Namespace("build", "b")
        import_namespace = Namespace("import", "i", host_dict)
        sub_import_namespace = Namespace("sub-import", "s")

        # Handle sub imports
        self._execute_sub_import(
            sub_import,
            import_namespace,
            sub_import_namespace
        )
        # Load the host vars in the inventory
        self._load_element_vars(
            element_index, host_dict,
            inventory,
            host_vars,
            build_namespace,
            import_namespace,
            sub_import_namespace
        )
        # Add the host to its main type group (devices, racks, etc.)
        # and to the group 'all'
        self._add_element_to_group(
            element_name=element_index, group_name=obj_type,
            inventory=inventory
        )
        self._add_element_to_group(
            element_name=element_index, group_name='all', inventory=inventory
        )

        # If the group_by option is specified, insert the element in the
        # propper groups.
        if group_by:
            # Iterate over every groups
            for group in group_by:
                # The 'tags' field is a list, a second iteration must be
                # performed at a deeper level
                if group == 'tags':
                    # Iterate over every tag
                    for tag in host_dict.get(group):
                        # Add the optional prefix
                        if group_prefix is None:
                            group_name = tag
                        else:
                            group_name = group_prefix + tag
                        # Insert the element in the propper group
                        self._add_element_to_group(
                            element_name=element_index,
                            group_name=group_name,
                            inventory=inventory
                        )
                else:
                    # Check that the specified group points towards an
                    # actual value
                    group_name = self._resolve_expression(
                        key_path=group,
                        build_ns=build_namespace,
                        import_ns=import_namespace,
                        sub_import_ns=sub_import_namespace
                    )
                    if group_name is not None:
                        # Add the optional prefix
                        if group_prefix:
                            group_name = group_prefix + group_name
                        # Insert the element in the propper group
                        self._add_element_to_group(
                            element_name=element_index,
                            group_name=group_name,
                            inventory=inventory
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
        app_obj = getattr(self.nb, application)
        endpoint = getattr(app_obj, object_type)

        # specific host handling
        if specific_host is not None:
            result = endpoint.filter(name=specific_host)
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

    def _resolve_expression(self, key_path,
                            build_ns, import_ns, sub_import_ns):
        """Resolve the given key path to a value.

        Args:
            key_path (str): The path toward the key
            data (dict): The actual host data dict that holds
                the target value.

        Returns:
            The target value
        """
        t = KeyPathTransformer(
            build_ns=build_ns,
            import_ns=import_ns,
            sub_import_ns=sub_import_ns
        )
        return t.transform(self.key_path_parser.parse(key_path))


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
    sub_import_def = {
        "type": "object",
        "required": ["stack", "vars"],
        "properties": {
            "stack": {
                "type": "string"
            },
            "vars": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "maxProperties": 1,
                    "minProperties": 1,
                    "patternProperties": {
                        "\\w+": {
                            "type": "object",
                            "properties": {
                                "application": {
                                    "type": "string"
                                },
                                "type": {
                                    "type": "string"
                                },
                                "index": {
                                    "type": "string"
                                },
                                "filter": {
                                    "type": "object",
                                    "patternProperties": {
                                        "\\w+": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

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
                            "\\w+": {
                                "type": "object",
                                "description": "The import section",
                                "minProperties": 1,
                                "additionalProperties": False,
                                "patternProperties": {
                                    "\\w+": {
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
                                            "sub_import": sub_import_def,
                                            "group_prefix": {
                                                "type": "string",
                                            },
                                            "filters": {
                                                "type": "object",
                                                "minProperties": 1
                                            },
                                            "host_vars": {
                                                "type": "array",
                                                "minItems": 1,
                                                "items": {
                                                    "type": "object",
                                                    "minProperties": 1,
                                                    "maxProperties": 1
                                                }
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
