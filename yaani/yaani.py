#!/usr/bin/env python3
from __future__ import absolute_import

from functools import reduce
import logging
import argparse
import sys
import os
import yaml
import importlib.util
try:
    import json
except ImportError:
    import simplejson as json

from lark import Lark, Transformer
import re

from jsonschema import validate
from jsonschema.exceptions import ValidationError
import pynetbox
from pynetbox.core.query import RequestError
import pyjq

# The name of the Environment variable where to find the path towards the
# configuration file
DEFAULT_ENV_CONFIG_FILE = "YAANI_CONFIG_FILE"
DEFAULT_ENV_MODULES_DIR = "YAANI_MODULES_PATH"


class error:
    BAD_PYNETBOX_API_ARGS = {
        "msg": "The arguments given for Netbox API connection are incorrect",
        "code": 1
    }
    CANNOT_OPEN_CONFIG_FILE = {
        "msg": "Cannot open configuration file.\n{}",
        "code": 2
    }
    CANNOT_PARSE_CONFIG_FILE = {
        "msg": "Unable to parse configuration file: \n{}",
        "code": 3
    }
    BAD_CONFIG_FILE_STRUCTURE = {
        "msg": "The configuration file is wrongly structured: \n{}",
        "code": 4
    }
    CANNOT_COMPUTE_GEN_ID = {
        "msg": (
            "The id key is not present in an unnamed host. "
            "Generic identifier cannot be computed \n"
        ),
        "code": 5
    }
    BAD_API_ENDPOINT = {
        "msg": "The netbox api endpoint {}/{}/ could not be found.",
        "code": 6
    }
    CUSTOM_MODULE_NOT_IMPORTED = {
        "msg": "The custom module {} could not be imported.",
        "code": 7
    }
    CUSTOM_MODULE_NOT_FOUND = {
        "msg": "The custom module {} could not be found: \n{}",
        "code": 8
    }
    CUSTOM_FUNC_NOT_FOUND = {
        "msg": (
            "The custom function {} could not be found in the custom "
            "module {}"
        ),
        "code": 9
    }
    CUSTOM_ARGS = {
        "msg": "Could not parse custom module and function names",
        "code": 10
    }
    JQ_PROCESSING = {
        "msg": "An error occured with the following jq query: {}\n{}",
        "code": 11
    }
    CUSTOM_EXECUTION_FAILED = {
        "msg": "An error occured during custom function {} execution: \n{}",
        "code": 12
    }
    BAD_SI_KEY = {
        "msg": (
            "Bad key '{}' in sub-import section. Variable not defined in "
            "sub_import['vars'] section."
        ),
        "code": 13
    }
    NON_UNIQUE_SI_VALUE = {
        "msg": (
            "The key '{}', specified as an sub-import index key, leads to a "
            "non unique value. Each key of the resulting dict must be "
            "unique. Try using a different variable name as index."
        ),
        "code": 14
    }


def exit(error, *args):
    sys.stderr.write(error["msg"].format(*args))
    sys.exit(error["code"])


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
            exit(error.BAD_SI_KEY, loading_var)

        # Access netbox API endpoint of wanted object
        app = getattr(
            self._api_connector,
            var_configuration['application']
        )
        endpoint = getattr(app, var_configuration['type'])

        # Resolve the actual filter value
        # ex: "device_id": "id" --> "device_id": 123
        filter_args = {}
        for parent_key, child_keypath in var_configuration['filter'].items():
            filter_args[parent_key] = resolve_expression(
                child_keypath, parent_namespace, first=True
            )

        # fetch sub elements from netbox
        if "id" in list(filter_args.keys()):
            elements = [endpoint.get(filter_args.get("id"))]
        else:
            elements = endpoint.filter(**filter_args)

        # Set the name of the key that will be used for index
        list_mode = False
        try:
            index_key_name = var_configuration['index']
        except KeyError:
            list_mode = True

        ret = {}
        acc = 0
        for e in elements:
            # Resolve the actual index value
            if list_mode:
                index_value = str(acc)
                acc += 1
            else:
                index_value = getattr(e, index_key_name)

            if index_value in list(ret.keys()):
                # The index key must lead to a unique value, avoid duplicate
                # e[index_key] must be unique
                exit(error.NON_UNIQUE_SI_VALUE, index_value)
            ret[index_value] = dict(e)
        return ret

    def stack(self, n):
        return n[0]

    def nested_path(self, n):
        """Treat the nested_path grammar rule

        Args:
            n (list): The list of children nodes. Here, variable names
                separated by dots.

        Returns:
            dict: Description
        """
        sub_pointer = [self._namespaces['sub-import']]
        # At first, the parent namespace is the data extracted from Netbox.
        parent_ns = self._namespaces['import']

        for var_name in map(lambda x: str(x), n):
            l = []
            # Go in depth
            for v in sub_pointer:
                if parent_ns is None:
                    parent_ns = v
                v[var_name] = self._import_var(
                    parent_namespace=parent_ns,
                    loading_var=var_name
                )
                l += list(v[var_name].values())
            # Nullify the parent namespace
            parent_ns = None
            sub_pointer = l

        return self._namespaces


class InventoryBuilder:
    """Inventory Builder is the object that builds and return the inventory.
    """
    def __init__(self, script_args, script_config):
        # Script args
        self._config_file = script_args['config_file']
        self._host = script_args['host']
        self._list_mode = script_args['list']

        # Configuration file
        self._config_data = script_config['netbox']
        self._config_api = self._config_data['api']
        self._import_section = self._config_data.get('import', {})

        # Create the api connector
        try:
            self._nb = pynetbox.api(**self._config_api)
        except TypeError:
            exit(error.BAD_PYNETBOX_API_ARGS)

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
        if not (self._list_mode or self._host):
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
            for app_name, app_import in list(iterator.items()):
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
        # Fetch the list of entities from Netbox
        netbox_hosts_list = self._get_elements_list(
            application,
            import_type,
            import_options=import_options,
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
                import_options=import_options
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
                    namespaces['build'][key] = self._resolve_expression(
                        key_path=value,
                        namespaces=namespaces
                    )

            # Add the loaded variables in the inventory under the proper
            # section (name of the host)
            inventory['_meta']['hostvars'].update(
                {element_name: namespaces['build']}
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
                                  obj_type, import_options={}):
        # Declare namespaces
        namespaces = {
            "import": host_dict,
            "build": {},
            "sub-import": {}

        }

        # Extract configuration statements from import options
        group_by = import_options.get('group_by', None)
        group_prefix = import_options.get('group_prefix', "")
        host_vars = import_options.get('host_vars', [])
        sub_import = import_options.get('sub_import', [])

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
                            group_name = group_prefix + str(value)
                            # Insert the element in the propper group
                            self._add_element_to_group(
                                element_name=element_index,
                                group_name=group_name,
                                inventory=inventory
                            )
                    else:
                        # Add the optional prefix
                        group_name = group_prefix + str(computed_group)
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
            namespaces (dict): The dict of namespaces

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

        return resolve_expression(s[-1], ns, first)

    def _add_element_to_group(self, element_name, group_name, inventory):
        inventory = self._initialize_group(
            group_name=group_name,
            inventory=inventory
        )
        if element_name not in inventory.get(group_name, {}).get('hosts', []):
            inventory[group_name]['hosts'].append(element_name)
        return inventory

    def _get_elements_list(self, application, object_type,
                           import_options={}, specific_host=None):
        """Retrieves a list of element from netbox API.

        Returns:
            A list of all elements from netbox API.

        Args:
            application (str): The name of the netbox application
            object_type (str): The type of object to import
            import_options (dict, optional): The options of import
            specific_host (str, optional): The name of a specific host which
                host vars must be returned alone.
        """
        app_obj = getattr(
            self._nb,
            application
        )
        endpoint = getattr(app_obj, object_type)

        filters = import_options.get("filters", None)

        # specific host handling
        if specific_host is not None:
            result = endpoint.filter(name=specific_host)
        elif filters is not None:
            tmp_result = []
            for args_array in filters:
                if "id" in list(args_array.keys()):
                    tmp_result += [endpoint.get(args_array.get("id"))]
                else:
                    tmp_result += endpoint.filter(**args_array)
            # Remove duplicates in the list in order to not execute actions
            # on the samed elements several times
            id_list = []
            result = []

            for h in tmp_result:
                if h.id not in id_list:
                    id_list.append(h.id)
                    result.append(h)

        else:
            result = endpoint.all()

        if result is None:
            result = []

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
                exit(error.CANNOT_COMPUTE_GEN_ID)
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
        default=os.getenv(
            DEFAULT_ENV_CONFIG_FILE, os.getcwd() + "/netbox.yml"
        ),
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
                                                "type": "array",
                                                "minItems": 1,
                                                "items": {
                                                    "type": "object",
                                                    "minProperties": 1
                                                }
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
    try:
        v = validate(instance=configuration, schema=config_schema)
    except ValidationError as err:
        exit(error.BAD_CONFIG_FILE_STRUCTURE, err)
    return v


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
        exit(error.CANNOT_OPEN_CONFIG_FILE, io_error)
    except yaml.YAMLError as yaml_error:
        # Handle Yaml level exceptions
        exit(error.CANNOT_PARSE_CONFIG_FILE, yaml_error)

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
        jq_method = pyjq.first
    else:
        jq_method = pyjq.all
    try:
        return jq_method(query, namespace)
    except Exception as err:
        exit(error.JQ_PROCESSING, query, err)


def render_inventory(render_configuration, inventory):
    if render_configuration:
        func_array = []
        for fdef in render_configuration:
            try:
                custom_module_name = fdef['module']
                func_name = fdef['name']
            except KeyError:
                exit(error.CUSTOM_ARGS)

            try:
                # Define a default dir for custom modules
                default_dir = os.getcwd() + "/modules"
                # Select the proper modules dir
                mod_dir = os.getenv(DEFAULT_ENV_MODULES_DIR, default_dir)
                # Build full modules path
                module_path = "%s/%s.py" % (mod_dir, custom_module_name)
                spec = importlib.util.spec_from_file_location(
                    custom_module_name, module_path
                )
                custom_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(custom_module)
            except ImportError:
                exit(error.CUSTOM_MODULE_NOT_IMPORTED, custom_module_name)
            except FileNotFoundError as err:
                exit(
                    error.CUSTOM_MODULE_NOT_FOUND,
                    custom_module_name,
                    str(err)
                )

            try:
                custom_func = getattr(custom_module, func_name)
            except AttributeError:
                exit(
                    error.CUSTOM_FUNC_NOT_FOUND,
                    func_name,
                    custom_module_name
                )

            func_array.append(custom_func)

        for f in func_array:
            try:
                inventory = f(inventory)
            except Exception as err:
                exit(error.CUSTOM_EXECUTION_FAILED, f, err)

    dump_json_inventory(inventory)


def cli(cli_argv):
    # Parse cli args
    args = vars(parse_cli_args(cli_argv[1:]))
    # Parse the configuration file
    configuration = load_config_file(args['config_file'])

    # Build the inventory
    builder = InventoryBuilder(args, configuration)
    inventory = builder.build_inventory()

    # Print the JSON formatted inventory dict
    render_inventory(
        configuration['netbox'].get('render', {}),
        inventory
    )

if __name__ == '__main__':
    cli(sys.argv)
