#!/usr/bin/env python3
from __future__ import absolute_import

from functools import reduce
import logging
import argparse
import sys
import os
import yaml
import importlib
try:
    import json
except ImportError:
    import simplejson as json

from lark import Lark, Transformer
import re

from jsonschema import validate
import pynetbox

import pyjq

# The name of the Environment variable where to find the path towards the
# configuration file
DEFAULT_ENV_CONFIG_FILE = "NETBOX_CONFIG_FILE"
DEFAULT_MODULES_DIR = "modules"


class StackTransformer(Transformer):
    """Provides an AST visitor. It is used to implement the feature of
    importing from netbox sub-elements joined together by certain parameters.
    """
    def __init__(self, vars_definition, api_connector, namespaces):
        """Constructor of the stack transformer.

        Args:
            vars_definition (dict): The dict containing the definition
                of the vars referenced in the stack string
            api_connector (pynetbox.api): The connector to the netbox api
                in the sub-import section.
            namespaces (dict): The namespaces used to resolve sub-imports
        """
        self._api_connector = api_connector
        self._vars_definition = vars_definition
        self._namespaces = namespaces

    def _import_var(self, parent_namespace, loading_var):
        # Access var configuration
        try:
            var_configuration = self._vars_definition[loading_var]
        except KeyError:
            # The var is not declared, exit program.
            sys.exit(
                "Bad key %s in sub-import section. Variable not defined in "
                "sub_import.vars section." % loading_var
            )

        # Access netbox API endpoint of wanted object
        try:
            app = getattr(
                self._api_connector,
                var_configuration['application']
            )
            endpoint = getattr(app, var_configuration['type'])
        except AttributeError:
            sys.exit(
                "The netbox api endpoint %s/%s/ "
                "cannot be found" % (
                    var_configuration['application'],
                    var_configuration['type']
                )
            )

        # Resolve the actual filter value
        # ex: "device_id": "id" --> "device_id": 123
        filter_args = {}
        for k, v in var_configuration['filter'].items():
            try:
                filter_args[k] = resolve_expression(
                    v, parent_namespace, first=True
                )
            except KeyError:
                sys.exit(
                    "The key given as a filter value '%s' does not exist." % v
                )

        # fetch sub elements from netbox
        if "id" in list(filter_args.keys()):
            elements = [endpoint.get(filter_args.get("id"))]
        else:
            elements = endpoint.filter(**filter_args)

        # Set the name of the key that will be used for index
        index_key_name = var_configuration['index']

        ret = {}
        for e in elements:
            # Resolve the actual index value
            index_value = getattr(e, index_key_name)

            if index_value in list(ret.keys()):
                # The index key must lead to a unique value, avoid duplicate
                # e[index_key] must be unique
                sys.exit(
                    "The key '%s', specified as an index key, is resolved to "
                    "non unique values." % index_value
                )
            ret[index_value] = dict(e)
        return ret

    def stack(self, n):
        return n[0]

    def nested_path(self, n):
        sub_pointer = [self._namespaces['sub-import']]
        parent_ns = self._namespaces['import']

        for path in map(lambda x: str(x), n):
            l = []
            for v in sub_pointer:
                if parent_ns is None:
                    parent_ns = v
                v[path] = self._import_var(
                    parent_namespace=parent_ns,
                    loading_var=path
                )
                l += list(v[path].values())
            parent_ns = None
            sub_pointer = l

        return self._namespaces


class InventoryBuilder:
    """Inventory Builder is the object that builds and return the inventory.
    """
    def __init__(self, script_args, script_config):
        # Script args
        self._config_file = script_args.config_file
        self._host = script_args.host
        self._list_mode = script_args.list

        # Configuration file
        self._config_data = script_config['netbox']
        self._config_api = self._config_data['api']
        self._import_section = self._config_data.get('import', None)

        # Create the api connector
        self._nb = pynetbox.api(**self._config_api)

        # Expression resolutions objects

        stack_grammar = """
            stack: nested_path

            nested_path: VAR ("." VAR)*
            VAR: /\\w+/
        """

        self._stack_parser = Lark(
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
        if not self._list_mode and not self._host:
            return {}

        inventory = self._init_inventory()

        if self._list_mode:

            if self._import_section:
                # Check whether the import section exists.
                iterator = self._import_section
            else:
                # Set the default behaviour args
                iterator = {
                    "dcim": {
                        "devices": {}
                    }
                }

            # For each application, iterate over all inner object types
            for app_name, app_import in list(self._import_section.items()):
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
                self._import_section
                .get('dcim', {})
                .get('devices', {})
            )

            self._execute_import(
                application='dcim',
                import_type='devices',
                import_options=device_import_options,
                inventory=inventory
            )

            return inventory['_meta']['hostvars'].get(self._host, {})

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
        host_vars_section = import_options.get('host_vars', [])
        sub_import = import_options.get('sub_import', [])

        # Fetch the list of entities from Netbox
        netbox_hosts_list = self._get_elements_list(
            application,
            import_type,
            filters=filters,
            specific_host=self._host
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

    def _load_element_vars(self, element_name, inventory, host_vars,
                           namespaces):
        """Enrich build namespace with hostvars configuration.
        """
        # If there is no required host var to load, do nothing.
        if host_vars:
            # Iterate over every key value pairs in host_vars required in
            # config file
            for d in host_vars:
                for key, value in d.items():
                    try:
                        namespaces['build'][key] = self._resolve_expression(
                            key_path=value,
                            namespaces=namespaces
                        )
                    except KeyError:
                        sys.exit("Error: Key '%s' not found" % value)

            # Add the loaded variables in the inventory under the proper
            # section (name of the host)
            inventory['_meta']['hostvars'].update(
                {element_name: dict(namespaces['build'])}
            )

    def _execute_sub_import(self, sub_import, namespaces):
        """Enrich sub import namespace with configured sub elements
        from netbox.
        """
        # Extract stack string
        stack_string = sub_import['stack']

        # Extract vars definition
        vars_definition = {}
        for i in sub_import['vars']:
            vars_definition.update(i)

        t = StackTransformer(
            api_connector=self._nb,
            vars_definition=vars_definition,
            namespaces=namespaces
        )
        return t.transform(self._stack_parser.parse(stack_string))

    def _add_element_to_inventory(self, element_index, host_dict, inventory,
                                  obj_type, group_by=None, group_prefix=None,
                                  host_vars=None, sub_import=[]):
        # Declare namespaces
        namespaces = {
            "import": dict(host_dict),
            "build": {},
            "sub-import": {}

        }

        # Handle sub imports
        for imports in sub_import:
            self._execute_sub_import(
                sub_import=imports,
                namespaces=namespaces
            )

        # Load the host vars in the inventory
        self._load_element_vars(
            element_name=element_index,
            inventory=inventory,
            host_vars=host_vars,
            namespaces=namespaces
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

        self._execute_group_by(
            element_index=element_index,
            group_by=group_by,
            group_prefix=group_prefix,
            inventory=inventory,
            namespaces=namespaces
        )

    def _execute_group_by(self, element_index, group_by, group_prefix,
                          inventory, namespaces):
        # If the group_by option is specified, insert the element in the
        # propper groups.
        if group_by:
            # Iterate over every groups
            for group in group_by:
                # Check that the specified group points towards an
                # actual value
                computed_group = self._resolve_expression(
                    key_path=group,
                    namespaces=namespaces
                )
                if computed_group is not None:
                    if type(computed_group) is list:
                        # Iterate over every tag
                        for value in computed_group:
                            # Add the optional prefix
                            if group_prefix is None:
                                group_name = value
                            else:
                                group_name = group_prefix + value
                            # Insert the element in the propper group
                            self._add_element_to_group(
                                element_name=element_index,
                                group_name=group_name,
                                inventory=inventory
                            )
                    else:
                        # Add the optional prefix
                        if group_prefix:
                            group_name = group_prefix + computed_group
                        else:
                            group_name = computed_group
                        # Insert the element in the propper group
                        self._add_element_to_group(
                            element_name=element_index,
                            group_name=group_name,
                            inventory=inventory
                        )

    def _resolve_expression(self, key_path, namespaces):
        """Resolve the given key path to a value.

        Args:
            key_path (str): The path toward the key
            build_ns (dict): The namespace corresponding build phase
            import_ns (dict): The namespace corresponding import phase
            sub_import_ns (dict): The namespace corresponding sub-import phase

        Returns:
            The target value
        """
        ns_select = {
            "b": "build",
            "i": "import",
            "s": "sub-import"
        }

        first = True
        ns = None

        s = key_path.split("#")
        # Check if there are command letters
        if len(s) > 1:
            # For each letter in the command, activate the proper options
            for cmd in s[0]:
                if cmd in list(ns_select.keys()):
                    ns = namespaces[ns_select[cmd]]
                elif cmd == 'l':
                    first = False
        # If the namespace was not defined, set it to default
        if ns is None:
            ns = namespaces["import"]

        r = resolve_expression(s[-1], ns, first)
        return r

    def _add_element_to_group(self, element_name, group_name, inventory):
        self._initialize_group(group_name=group_name, inventory=inventory)
        if element_name not in inventory.get(group_name).get('hosts'):
            inventory[group_name]['hosts'].append(element_name)

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
        try:
            app_obj = getattr(
                self._nb,
                application
            )
            endpoint = getattr(app_obj, object_type)
        except AttributeError:
            sys.exit(
                "The netbox api endpoint %s/%s/ "
                "cannot be found" % (
                    application,
                    object_type
                )
            )

        # specific host handling
        if specific_host is not None:
            result = endpoint.filter(name=specific_host)
        elif filters is not None:
            if "id" in list(filters.keys()):
                result = [endpoint.get(filters.get("id"))]
            else:
                result = endpoint.filter(**filters)
        else:
            result = endpoint.all()

        return result

    def _get_identifier(self, host, obj_type):
        """Return an identifier for the given host.

        Args:
            host (str): The name of the host
            obj_type (str): The type of the object

        Returns:
            str: The computed id
        """
        # Get the 'name' field value of the specified host
        r = host.get('name', None)
        # If the 'name' field is empty, compute the id :
        #   <object type>_<id in netbox db>
        if r is None or r == "":
            try:
                r = "%s_%s" % (obj_type, host['id'])
            except KeyError:
                sys.exit(
                    "The id key is not present in an unnamed host. Generic "
                    "identifier cannot be computed"
                )
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
        "type": "array",
        "minItems": 1,
        "items": {
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
    }

    config_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://example.com/product.schema.json",
        "title": "Configuration file",
        "description": "The configuration file of the dynamic inventory",
        "type": "object",
        "required": ["netbox"],
        "properties": {
            "netbox": {
                "type": "object",
                "description": "The base key of the configuration file",
                "required": ["api"],
                "additionalProperties": False,
                "properties": {
                    "api": {
                        "type": "object",
                        "description": (
                            "The section holding information used "
                            "to connect to netbox api"
                        ),
                        "additionalProperties": False,
                        "required": ["url"],
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
                    },
                    "render": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["module", "name"],
                            "properties": {
                                "module": {
                                    "type": "string"
                                },
                                "name": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                }
            }
        }
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


def resolve_expression(query, namespace, first):
    if first:
        return pyjq.first(query, namespace)
    return pyjq.all(query, namespace)


def render_inventory(render_configuration, inventory):
    if render_configuration:
        func_array = []
        for fdef in render_configuration:
            try:
                custom_module_name = fdef['module']
                func_name = fdef['name']
            except KeyError:
                sys.exit("Could not parse custom module and function names")

            try:
                module_name = (
                    "%s.%s" % (
                        DEFAULT_MODULES_DIR,
                        custom_module_name
                    )
                )
                custom_module = importlib.import_module(module_name)
            except ImportError:
                sys.exit(
                    "The custom module %s could not be "
                    "imported" % (module_name)
                )

            try:
                custom_func = getattr(custom_module, func_name)
            except AttributeError:
                sys.exit(
                    "The custom function %s could not be found in the custom "
                    "module" % (func_name)
                )

            func_array.append(custom_func)

        for f in func_array:
            inventory = f(inventory)

    dump_json_inventory(inventory)


def main():
    # Parse cli args
    args = parse_cli_args(sys.argv[1:])
    # Parse the configuration file
    configuration = load_config_file(args.config_file)

    # Build the inventory
    builder = InventoryBuilder(args, configuration)
    inventory = builder.build_inventory()

    # Print the JSON formatted inventory dict
    render_inventory(
        configuration['netbox'].get('render', {}),
        inventory
    )


if __name__ == '__main__':
    main()
