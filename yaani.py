#!/usr/bin/env python3

from __future__ import absolute_import

import argparse
import sys
import os
import requests
import yaml
try:
	import json
except ImportError:
	import simplejson as json

# The name of the Environment variable where to find the path towards the configuration file
DEFAULT_ENV_CONFIG_FILE = "NETBOX_CONFIG_FILE"

def safe_url(url):
	"""Return the given URL string making sure it ends with a slash

	Args:
		url (str): The URL

	Returns:
		TYPE: The URL ending with a trailing slash
	"""
	if url and url[-1] != '/':
		return url + '/'
	else:
		return url


def parse_cli_args(script_args):
	"""Declare and configure script argument parser

	Args:
			script_args (list): The list of script arguments

	Returns:
			obj: The parsed arguments in an object. See argparse documention (https://docs.python.org/3.7/library/argparse.html) for more information.
	"""
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--config-file', help="""Path for script's configuration file. If None is specified,
														default value is %s environment variable or netbox.yml in the current dir.""" % DEFAULT_ENV_CONFIG_FILE,
						default=os.getenv(DEFAULT_ENV_CONFIG_FILE, "netbox.yml"))
	parser.add_argument('--list', action='store_true', help='Print the entire inventory with hostvars respecting the Ansible dynamic inventory syntax.')
	parser.add_argument('--host', action='store', help='Print specific host vars as Ansible dynamic inventory syntax.')

	# Parse script arguments and return the result
	return parser.parse_args(script_args)


def validate_key_path(key_path):
	"""Return true if the given key_path syntax is valid.

	Args:
			key_path (str): The key-path

	Returns:
			Bool: True if the key-path syntax is ok. False else
	"""
	key_list = key_path.split(".")
	for key in key_list:
		if key == "":
			return False
	return True


def raise_for_configuration_errors(configuration):
	"""Validate the configuration structure. If no error is found, nothing happens.

	Args:
			configuration (dict): The parsed configuration
	"""
	def check_mandatory_key(key_name, data_dict):
		"""Trigger a sys.exit if the specified key name is not in the given dict.

		Args:
			key_name (str): The key name
			data_dict (dict): The dict in which the search must occur
		"""
		main_key_error = "Error: The main key '%s' is not present in the configuration file."
		if not key_name in list(data_dict.keys()):
			sys.exit(main_key_error % key_name)

	# Allowed import types declaration
	import_types = ['devices', 'racks', 'sites']

	# Error messages declaration
	key_path_error = "Error: The main key '%s' is not present in the configuration file."

	check_mandatory_key('netbox', configuration)
	root = configuration['netbox']

	# Check that main sections exist
	check_mandatory_key('api', root)

	# Ensure the mandatory key 'api_url' is set
	check_mandatory_key('api_url', root['api'])

	# Check values of import section
	root = root.get('import', None)
	if root:
		for key, import_statement in root.items():
			# Make sure the import type value is supported
			if not key in import_types:
				sys.exit("Error: The import type %s is not supported." % key)
			try:
				# Validate the group-by syntax
				for prop in import_statement.get('group_by'):
					if not validate_key_path(prop):
						sys.exit(key_path_error % prop)
			except KeyError:
				continue
			except TypeError:
				continue


def load_config_file(config_file_path):
	""" Load the configuration file and returns its parsed content.

	Args:
			config_file_path (str): The path towards the configuration file
	"""
	try:
		with open(config_file_path, 'r') as file:
			try:
				parsed_config = yaml.safe_load(file)
			except yaml.YAMLError as yaml_error:
				# Handle Yaml level exceptions
				sys.exit("Error: Unable to parse configuration file: %s" %
						 yaml_error)
	except IOError as io_error:
		# Handle file level exception
		sys.exit("Error: Cannot open configuration file.\n%s" % io_error)

	# If syntax of configuration file is valid, nothing happens
	# Beware, syntax can be valid while semantic is not
	raise_for_configuration_errors(parsed_config)

	return parsed_config


class InventoryBuilder:
	"""Inventory Builder is the object that builds and return the inventory.

	Attributes:
		api_token (str): The token to use with Netbox
		api_url (str): The Netbox API URL
		config_data (dict): The configuration parsed from the configuration file
		config_file (str): The path of thge configuration file
		host (str): The hostname if specified, None else
		imports (list): The list of import statements in the configuration file
		list_mode (bool): The value of --list option
	"""

	def __init__(self, script_args, script_config):
		# Script args
		self.config_file = script_args.config_file
		self.host = script_args.host
		self.list_mode = script_args.list

		# Configuration file
		self.config_data = script_config['netbox']
		self.api_url = safe_url(self.config_data['api'].get('api_url', None))
		self.api_token = self.config_data['api'].get('api_token', None)
		self.imports = self.config_data.get('import', None)

	def _init_inventory(self):
		return {'_meta': {'hostvars': {}}}

	def build_inventory(self):
		#  If none of the list or host options is set, return an empty dict
		if self.list_mode:

			inventory = self._init_inventory()

			if self.imports:
				# Iterate through each import element and resolve it
				for type_key, import_statement in self.imports.items():
					self._execute_import(
						import_type=type_key, import_options=import_statement, inventory=inventory)
			else:
				# By default, get all devices and handle no grouping option
				self._execute_import(import_type='devices',
									 import_options={}, inventory=inventory)

			return inventory
		elif self.host:
			inventory = self._init_inventory()

			# a host is considered to be a device. Check if devices import options are set.
			device_import_options = self.imports.get('devices', {})

			self._execute_import(import_type='devices',
								 import_options=device_import_options, inventory=inventory)

			return inventory['_meta']['hostvars'][self.host]
		else:
			# nothing to return, nothing to generate
			return {}

	def _execute_import(self, import_type, import_options, inventory):
		import_types_endpoints = {
			"devices": "dcim/devices/",
			"racks": "dcim/racks/",
			"sites": "dcim/sites/",
		}
		# Ensure the import type is known and supported
		try:
			endpoint = import_types_endpoints[import_type]
		except KeyError:
			sys.exit(
				"Error: %s type is not supported under import section." % import_type)

		netbox_hosts_list = self._get_elements_list(self.api_url + endpoint,
													api_token=self.api_token,
													cfilter=import_options.get(
														'filter', None),
													specific_host=self.host)
		if netbox_hosts_list:
			for host in netbox_hosts_list:
				self._add_element_to_inventory(
					host, inventory, import_type, import_options.get('group_by', None), import_options.get('group_prefix', None))
				self._load_element_vars(
					host, inventory, import_options.get('host_vars', None))

	def _ensure_group_exists(self, group_name, inventory):
		inventory.setdefault(group_name, {})
		inventory[group_name].setdefault('hosts', [])
		return inventory

	def _load_element_vars(self, host, inventory, host_vars=None):
		# If there is no required host var to load, end here.
		if host_vars:
			host_data = {}
			# Iterate over every key value pairs in host_vars required in config file
			for key, value in host_vars.items():
				# Set the name of the key
				if value == 'ALL':
					host_data[key] = host
				else:
					try:
						host_data[key] = self._dig_value(
							key_path=value, data=host)
					except KeyError:
						sys.exit("Error: Key '%s' not found" % value)

			# Add the loaded variables in the inventory under the proper section (name of the host)
			inventory['_meta']['hostvars'].update(
				{host.get('name'): host_data})

	def _dig_value(self, key_path, data):
		key_path_list = key_path.split(".")

		pointer = data
		for key in key_path_list:
			try:
				if key in list(pointer.keys()):
					pointer = pointer[key]
				else:
					sys.exit(
						"Error: The key solving failed in key_path '%s'" % (key_path))
			except AttributeError:
				return None

		return pointer

	def _add_element_to_inventory(self, host, inventory, obj_type, group_by=None, group_prefix=None):
		element_name = host.get('name')
		if group_by:
			for group in group_by:
				if self._dig_value(key_path=group, data=host) != None:
					if group == 'tags':
						for tag in host.get(group):
							group_name = tag
							if group_prefix != None:
								group_name = group_prefix + group_name
							self._add_element_to_group(
								element_name=element_name, group_name=group_name, inventory=inventory)
					else:
						group_name = self._dig_value(key_path=group, data=host)
						if group_prefix:
							group_name = group_prefix + group_name
						self._add_element_to_group(
							element_name=element_name, group_name=group_name, inventory=inventory)
		# Anyway, add the host to its main type group: devices, racks etc.
		self._add_element_to_group(
			element_name=element_name, group_name=obj_type, inventory=inventory)

	def _add_element_to_group(self, element_name, group_name, inventory):
		self._ensure_group_exists(group_name=group_name, inventory=inventory)
		if not element_name in inventory.get(group_name).get('hosts'):
			inventory[group_name]['hosts'].append(element_name)

	def _get_elements_list(self, api_url, api_token=None, cfilter=None, specific_host=None):
		"""Retrieves hosts list from netbox API.

		Returns:
				A list of all hosts from netbox API.
		"""

		if not api_url:
			sys.exit("Missing API URL in configuration file")

		api_url_headers = {}
		api_url_params = {}

		if api_token:
			# load token in headers
			api_url_headers.update({"Authorization": "Token %s" % api_token})

		if specific_host:
			# narrow search to one specific host
			api_url_params.update({"name": specific_host})

		# Resolve the filter
		if cfilter:
			filter_string = "?%s&limit=0" % cfilter
		else:
			filter_string = "?limit=0"

		# Get hosts list without pagination
		api_output = requests.get(
			api_url + filter_string, params=api_url_params, headers=api_url_headers)

		# Check that a request is 200
		api_output.raise_for_status()

		# Get api output data.
		try:
			api_output_data = api_output.json()
		except json.decoder.JSONDecodeError:
			sys.exit(
				"Error: Error while parsing output from netbox. Possible mistake is you entered a URL forgetting the /api/ suffix.")

		# Get hosts list.
		return api_output_data["results"]


def dump_json_inventory(inventory):
	"""Dumps the given inventory in json

	Args:
			inventory (dict): The inventory
	"""
	print(json.dumps(inventory))


def main():
	args = parse_cli_args(sys.argv[1:])
	configuration = load_config_file(args.config_file)

	builder = InventoryBuilder(args, configuration)
	dump_json_inventory(builder.build_inventory())


if __name__ == '__main__':
	main()
