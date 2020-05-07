#!/usr/bin/env python3
from __future__ import absolute_import

from functools import reduce
from abc import ABC, abstractmethod
import requests
import argparse
import sys
import os
import yaml
import importlib.util
try:
    import json
except ImportError:
    import simplejson as json

from jsonschema import validate
from jsonschema.exceptions import ValidationError
import pynetbox
from pynetbox.core.query import RequestError
import pyjq

# The name of the Environment variable where to find the path towards the
# configuration file
DEFAULT_ENV_CONFIG_FILE = "YAANI_CONFIG_FILE"
DEFAULT_ENV_MODULES_DIR = "YAANI_MODULES_PATH"


class YaaniError(Exception):
    pass


class Validator:
    class DataSources:
        @staticmethod
        def validate_source_args(src_type, src_args):
            validation_scheme = {
                SourceLoader.SOURCE_TYPE.NETBOX_API: {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["url"],
                    "properties": {
                        "url": {
                            "type": "string",
                            "minLength": 1
                        },
                        "token": {
                            "type": "string",
                            "minLength": 1
                        },
                        "private_key": {
                            "type": "string",
                            "minLength": 1
                        },
                        "private_key_file": {
                            "type": "string",
                            "minLength": 1
                        },
                        "ssl_verify": {
                            "type": "boolean",
                        }
                    },
                    "allOf": [
                        {
                            "not": {
                                "required": [
                                    "private_key",
                                    "private_key_file"
                                ]
                            }
                        }
                    ]
                },
                SourceLoader.SOURCE_TYPE.FILE: {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "content_type"],
                    "properties": {
                        "path": {
                            "type": "string",
                            "minLength": 1
                        },
                        "content_type": {
                            "type": "string",
                            "enum": ["yaml", "json"],
                        }
                    }
                },
                SourceLoader.SOURCE_TYPE.SCRIPT: {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "content_type"],
                    "properties": {
                        "path": {
                            "type": "string",
                            "minLength": 1
                        },
                        "content_type": {
                            "type": "string",
                            "enum": ["yaml", "json"],
                        }
                    }
                }
            }

            try:
                schema = validation_scheme[src_type]
            except KeyError:
                raise YaaniError(
                    "The specified source type '{}' is not valid."
                    .format(src_type)
                )

            try:
                v = validate(
                    instance=src_args,
                    schema=schema
                )
            except ValidationError as err:
                raise YaaniError(
                    "The configuration file parsing failed due to an error in "
                    "the '{}' section: \n{}\n{}.".format(
                        src_type, err.instance, err.message
                    )
                )

        @staticmethod
        def validate_configuration(configuration):
            data_sources_section = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$id": "http://example.com/product.schema.json",
                "type": "object",
                "minProperties": 1,
                "patternProperties": {
                    "[A-Za-z0-9_-]+": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["type", "args"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    SourceLoader.SOURCE_TYPE.NETBOX_API,
                                    SourceLoader.SOURCE_TYPE.FILE,
                                    SourceLoader.SOURCE_TYPE.SCRIPT
                                ]
                            },
                            "args": {
                                "type": "object",
                                "minProperties": 1
                            }
                        }
                    }
                }
            }

            try:
                v = validate(
                    instance=configuration,
                    schema=data_sources_section
                )
            except ValidationError as err:
                raise YaaniError(
                    "The configuration file parsing failed due to an error in "
                    "the 'data_sources' section: \n{}\n{}".format(
                        err.instance, err.message
                    )
                )

            for _, src_def in configuration.items():
                Validator.DataSources.validate_source_args(
                    src_def['type'],
                    src_def['args']
                )

    class DataSets:
        @staticmethod
        def validate_configuration(configuration):
            schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$id": "http://example.com/product.schema.json",
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["from", "args", "name"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1
                        },
                        "from": {
                            "type": "string",
                            "enum": [
                                DataSetLoader.STRATEGY.SOURCE,
                                DataSetLoader.STRATEGY.MERGE,
                                DataSetLoader.STRATEGY.DECORATION,
                                DataSetLoader.STRATEGY.FILTERING,
                            ]
                        },
                        "args": {
                            "oneOf": [
                                {
                                    "type": "object",
                                },
                                {
                                    "type": "array",
                                },
                            ]
                        }
                    }
                }
            }

            try:
                v = validate(
                    instance=configuration,
                    schema=schema
                )
            except ValidationError as err:
                raise YaaniError(
                    "The configuration file parsing failed due to an error in "
                    "the 'data_sets' section: \n{}\n{}".format(
                        err.instance, err.message
                    )
                )

        @staticmethod
        def validate_data_set_args(strategy, args):
            value = {
                "type": "string",
                "minLength": 1
            }

            validation_scheme = {
                DataSetLoader.STRATEGY.NETBOX_SOURCE: {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "type": "object",
                    "required": ["name", "app", "type"],
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1
                        },
                        "app": {
                            "type": "string",
                            "minLength": 1
                        },
                        "type": {
                            "type": "string",
                            "minLength": 1
                        },
                        "filters": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "minProperties": 1
                            }
                        }
                    }
                },
                DataSetLoader.STRATEGY.FILE_SOURCE: {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "type": "object",
                    "required": ["name", "filter"],
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1
                        },
                        "filter": {
                            "type": "string",
                            "minLength": 1
                        }
                    }
                },
                DataSetLoader.STRATEGY.FILTERING: {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "type": "object",
                    "required": ["name", "filter"],
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1
                        },
                        "filter": {
                            "type": "string",
                            "minLength": 1
                        }
                    }
                },
                DataSetLoader.STRATEGY.MERGE: {
                    "definitions": {
                        "value": value
                    },
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "required": ["sets"],
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "sets": {
                            "type": "array",
                            "minItems": 2,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "pivot"],
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "minLength": 1
                                    },
                                    "pivot": {
                                        "$ref": "#/definitions/value"
                                    }
                                }
                            }
                        },
                        "keys": {
                            "type": "object",
                            "minProperties": 1,
                            "patternProperties": {
                                "[A-Za-z0-9_-]+": {
                                    "type": "string",
                                    "minLength": 1
                                }
                            }
                        }
                    }
                },
                DataSetLoader.STRATEGY.DECORATION: {
                    "definitions": {
                        "value": value
                    },
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://example.com/product.schema.json",
                    "type": "object",
                    "required": ["main", "decorators"],
                    "additionalProperties": False,
                    "properties": {
                        "main": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "pivot"],
                            "properties": {
                                "name": {
                                    "$ref": "#/definitions/value"
                                },
                                "pivot": {
                                    "$ref": "#/definitions/value"
                                },
                                "exclusive": {
                                    "type": "boolean"
                                }
                            }
                        },
                        "decorators": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "pivot", "anchor"],
                                "properties": {
                                    "name": {
                                        "$ref": "#/definitions/value"
                                    },
                                    "anchor": {
                                        "$ref": "#/definitions/value"
                                    },
                                    "pivot": {
                                        "$ref": "#/definitions/value"
                                    }
                                }
                            }
                        }
                    }
                },
            }

            try:
                schema = validation_scheme[strategy]
            except KeyError:
                # Already covered
                raise YaaniError(
                    "The specified strategy '{}' is not valid. Please choose "
                    "between:  - source\n  - merge\n  - decoration\n"
                    .format(strategy)
                )

            try:
                v = validate(
                    instance=args,
                    schema=schema
                )
            except ValidationError as err:
                raise YaaniError(
                    "The configuration file parsing failed due to an error in "
                    "the 'data_sets' section: \n{}\n{}."
                    .format(
                        err.instance, err.message
                    )
                )

    class Render:
        @staticmethod
        def validate_configuration(configuration):
            value = {
                "type": "object",
                "minProperties": 1,
                "required": ["value"],
                "additionalProperties": False,
                "properties": {
                    "value": {
                        "type": "string",
                        "minLength": 1
                    },
                    "namespace": {
                        "type": "string",
                        "enum": [
                            "import",
                            "build"
                        ]
                    }
                }
            }

            render_section = {
                "definitions": {
                    "value": value
                },
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$id": "http://example.com/product.schema.json",
                "type": "object",
                "additionalProperties": False,
                "required": ["elements"],
                "properties": {
                    "elements": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "args"],
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "minLength": 1
                                },
                                "args": {
                                    "type": "object",
                                    "minProperties": 1,
                                    "additionalProperties": False,
                                    "required": ["index"],
                                    "properties": {
                                        "pre_condition": {
                                            "type": "string",
                                            "minLength": 1
                                        },
                                        "post_condition": {
                                            "$ref": "#/definitions/value"
                                        },
                                        "group_by": {
                                            "type": "array",
                                            "minItems": 1,
                                            "items": {
                                                "$ref": "#/definitions/value"
                                            }
                                        },
                                        "group_prefix": {
                                            "type": "string",
                                        },
                                        "index": {
                                            "$ref": "#/definitions/value"
                                        },
                                        "host_vars": {
                                            "type": "object",
                                            "minProperties": 1,
                                            "patternProperties": {
                                                "[A-Za-z0-9_-]+": {
                                                    "type": "string",
                                                    "minLength": 1
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "group_vars": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["group", "set"],
                            "additionalProperties": False,
                            "properties": {
                                "group": {
                                    "type": "string",
                                    "minLength": 1
                                },
                                "set": {
                                    "type": "string",
                                    "minLength": 1
                                }
                            }
                        }
                    },
                    "group_hierarchy": {
                        "type": "object",
                        "minProperties": 1
                    }
                }
            }

            try:
                v = validate(
                    instance=configuration,
                    schema=render_section
                )
            except ValidationError as err:
                raise YaaniError(
                    "The configuration file parsing failed due to an error in "
                    "the 'render' section: \n{}\n{}".format(
                        err.instance, err.message
                    )
                )

    class Transform:
        @staticmethod
        def validate_configuration(configuration):
            transform = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$id": "http://example.com/product.schema.json",
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["module", "func"],
                    "properties": {
                        "module": {
                            "type": "string",
                            "minLength": 1
                        },
                        "func": {
                            "type": "string",
                            "minLength": 1
                        }
                    }
                }
            }

            try:
                v = validate(
                    instance=configuration,
                    schema=transform
                )
            except ValidationError as err:
                raise YaaniError(
                    "The configuration file parsing failed due to an error in "
                    "the 'transform' section: \n{}\n{}".format(
                        err.instance, err.message
                    )
                )


class SourceLoader:
    class Utils:
        @staticmethod
        def instantiate_source(src_type, args):
            """Instantiate and return an object corresponding to the given
            source type and args.
            """
            sources = {
                SourceLoader.SOURCE_TYPE.NETBOX_API: NetboxSource,
                SourceLoader.SOURCE_TYPE.FILE: FileSource,
                SourceLoader.SOURCE_TYPE.SCRIPT: ScriptSource,
            }
            try:
                # Determine the class to instantiate
                source_class = sources[src_type]
            except KeyError as err:
                raise YaaniError(
                    "The source type '{}' is not valid.".format(src_type)
                )

            try:
                # Actually instantiate the data source
                data_source = source_class(args)
            except TypeError as err:
                # The json schema should control args given at runtime
                # instantiation. If bad args were not to be filtered,
                # this is where the error will be handled
                raise YaaniError(
                    "The arguments given to '{}' source are not valid."
                    .format(str(src_type))
                )
            return data_source

    class SOURCE_TYPE:
        NETBOX_API = "netbox_api"
        FILE = "file"
        SCRIPT = "script"
        ORDER = {
            FILE: 3,
            SCRIPT: 2,
            NETBOX_API: 1,
        }

    def __init__(self, configuration={}):
        self._configuration = configuration

    @property
    def configuration(self):
        return self._configuration

    @configuration.setter
    def configuration(self, value):
        self._configuration = value

    def load_sources(self):
        """
        Returns:
            dict: A dictionnary referencing sources object.

        Raises:
            YaaniError: Raise an exception if a source is found to be
                defined twice.
        """
        sources = {}

        # For each data source definition, parse it and instantiate it
        for src_name, src_def in self._configuration.items():
            if len(src_name) == 0:
                raise YaaniError(
                    "A source name cannot be empty."
                )
            try:
                src_type = src_def["type"]
                src_args = src_def["args"]
            except KeyError as err:
                raise YaaniError(
                    "The source '{}' is missing the key '{}'.\n"
                    .format(src_name, err.args[0])
                )

            # Check for previous definition of the source
            if src_name in sources:
                raise YaaniError(
                    "The source '{}' is defined twice."
                    .format(src_name)
                )

            # Instantiate source
            try:
                sources[src_name] = SourceLoader.Utils.instantiate_source(
                    src_type,
                    src_args
                )
            except YaaniError as err:
                raise YaaniError(
                    "An error occured while instantiating source '{}'.\n{}"
                    .format(src_name, str(err))
                )

        return sources


class DataSetLoader:
    class Utils:
        @staticmethod
        def map_elt_to_value(query, elt_lst, overlap=False):
            # Map elt to their id
            tmp_dct = {
                id(elt): elt for elt in elt_lst
            }
            # Execute query on elt
            try:
                mpng = pyjq.first(
                    "[ .[] | [.[0], (.[1]{})]]".format(query),
                    list(tmp_dct.items())
                )
            except ValueError as err:
                raise YaaniError(
                    "The given query '{}' seems to be incorrect.\n"
                    .format(query)
                )
            # Convert the output lists to tuples
            mpng = [tuple(x) for x in mpng]

            result_dict = {}
            if overlap:
                for uid, indx in mpng:
                    if indx:
                        if isinstance(indx, list) or isinstance(indx, dict):
                            raise YaaniError(
                                "From query '{}'.\n"
                                "A list or a dict cannot be used as a pivot:\n"
                                "{}".format(query, indx)
                            )
                        result_dict.setdefault(indx, []).append(tmp_dct[uid])
            else:
                for uid, indx in mpng:
                    if indx:
                        if isinstance(indx, list) or isinstance(indx, dict):
                            raise YaaniError(
                                "From query '{}'.\n"
                                "A list or a dict cannot be used as a pivot:\n"
                                "{}".format(query, indx)
                            )
                        if indx in result_dict:
                            raise YaaniError(
                                "The query '{}' leads to non-unique values:\n"
                                "{}\n".format(query, indx)
                            )
                        else:
                            result_dict[indx] = tmp_dct[uid]

            return result_dict

        @staticmethod
        def create_dataset_from_source(config, sources):
            src_name = config["name"]
            try:
                # Use config as args for instanciation removing
                # the key 'name'
                lst = sources[src_name].extract({
                    k: v for k, v in config.items() if k != "name"
                })
            except KeyError:
                raise YaaniError(
                    "The source '{}' refers to an unexisting source."
                    .format(src_name)
                )

            return lst

        @staticmethod
        def create_dataset_from_merge(config, data_sets):
            sets = config["sets"]
            keys = config.get("keys", {})

            try:
                arg_lst = [
                    (arg["name"], arg["pivot"], data_sets[arg["name"]])
                    for arg in sets
                ]
            except KeyError as err:
                raise YaaniError(
                    "'{}' refers to an unexisting data_set."
                    .format(err.args[0])
                )
            return DataSetLoader.Utils.merge_sets(
                arg_lst,
                keys
            )

        @staticmethod
        def merge_sets(set_lst, keys):
            # Create an index for each set
            indxd_lst = []

            for name, pvt_args, data_set in set_lst:
                # Associate elts to their pivot query result
                try:
                    indxd_dct = DataSetLoader.Utils.map_elt_to_value(
                        pvt_args,
                        data_set
                    )
                except YaaniError as err:
                    raise YaaniError(
                        "The merge of set '{}' failed:\n{}"
                        .format(name, str(err))
                    )
                indxd_lst.append((name, indxd_dct))

            # Get the exhaustive index list without duplicates
            idxs = list(set(reduce(
                lambda x, y: x + y,
                [list(idx.keys()) for name, idx in indxd_lst]
            )))

            lst = []
            for cmptd in idxs:
                elts = [
                    (name, setcntnt.get(cmptd, {}))
                    for name, setcntnt in indxd_lst
                ]
                r = DataSetLoader.Utils.merge_elts([lst for name, lst in elts])
                if r:
                    # Handle priority keys
                    dsdct = dict(elts)
                    for k, ds in keys.items():
                        if k in dsdct.get(ds, {}):
                            r[k] = dsdct[ds][k]

                    lst.append(r)

            return lst

        @staticmethod
        def merge_elts(elts):
            # Invert list to priorize data from first elements
            elts.reverse()

            new_elt = {}
            for elt in elts:
                new_elt.update(elt)

            return new_elt

        @staticmethod
        def decorate_dataset(config, data_sets):
            exclusive = config["main"].get("exclusive", True)
            try:
                idx_main_set = DataSetLoader.Utils.map_elt_to_value(
                    config["main"]["pivot"],  # Pivot
                    data_sets[config["main"]["name"]],  # Data set
                    overlap=not exclusive
                )
            except KeyError as err:
                raise YaaniError(
                    "The set '{}' has not been declared.\n"
                    .format(err.args[0])
                )
            except YaaniError as err:
                raise YaaniError(
                    "The main set '{}' could not be decorated:\n{}"
                    .format(config["main"]["name"], str(err))
                )
            try:
                idx_add_set_lst = [
                    (
                        cfg["anchor"],
                        DataSetLoader.Utils.map_elt_to_value(
                            cfg["pivot"],
                            data_sets[cfg["name"]],
                            overlap=True
                        )
                    )
                    for cfg in config["decorators"]
                ]
            except KeyError as err:
                raise YaaniError(
                    "The set '{}' has not been declared.\n"
                    .format(err.args[0])
                )
            except YaaniError as err:
                raise YaaniError(
                    "One of the decorating sets could not be used.\n{}"
                    .format(str(err))
                )

            r_lst = []
            if exclusive:
                for idx, elt in idx_main_set.items():
                    sublst = [
                        (anchor, ds.get(idx))
                        for anchor, ds in idx_add_set_lst
                        if idx is not None and ds.get(idx)
                    ]
                    r_lst.append(
                        DataSetLoader.Utils.decorate_element(
                            elt,
                            sublst
                        )
                    )
            else:
                for idx, elt_list in idx_main_set.items():
                    sublst = [
                        (anchor, ds.get(idx))
                        for anchor, ds in idx_add_set_lst
                        if idx is not None and ds.get(idx)
                    ]
                    for elt in elt_list:
                        r_lst.append(
                            DataSetLoader.Utils.decorate_element(
                                elt,
                                sublst
                            )
                        )
            return r_lst

        @staticmethod
        def create_dataset_from_filtering(args, data_sets):
            query = args["filter"]
            ds_name = args["name"]
            try:
                ds = data_sets[ds_name]
            except KeyError:
                raise YaaniError(
                    "Unknown set '{}'\n"
                    .format(ds_name)
                )

            try:
                r = pyjq.first(
                    query,
                    ds
                )
            except ValueError as err:
                raise YaaniError(
                    "The given query seems to be incorrect: {}\n"
                    .format(query)
                )

            return r

        @staticmethod
        def decorate_element(elt, data):
            new_elt = {}
            new_elt.update(elt)
            for anchor, value in data:
                new_elt[anchor] = value

            return new_elt

        @staticmethod
        def create_set(strategy, args, sources, data_sets):
            # Select the proper method to execute
            if strategy == DataSetLoader.STRATEGY.SOURCE:
                data_set = DataSetLoader.Utils.create_dataset_from_source(
                    args,
                    sources
                )
            elif strategy == DataSetLoader.STRATEGY.FILTERING:
                data_set = DataSetLoader.Utils.create_dataset_from_filtering(
                    args,
                    data_sets
                )
            elif strategy == DataSetLoader.STRATEGY.MERGE:
                data_set = DataSetLoader.Utils.create_dataset_from_merge(
                    args,
                    data_sets
                )
            elif strategy == DataSetLoader.STRATEGY.DECORATION:
                data_set = DataSetLoader.Utils.decorate_dataset(
                    args,
                    data_sets
                )
            else:
                raise YaaniError(
                    "'{}' is not a valid strategy."
                    .format(strategy)
                )

            return data_set

    class STRATEGY:
        SOURCE = "source"
        NETBOX_SOURCE = "netbox_source"
        FILE_SOURCE = "file_source"
        MERGE = "merge"
        DECORATION = "decoration"
        FILTERING = "filtering"

    def __init__(self, configuration=[]):
        self._configuration = configuration

    @property
    def configuration(self):
        return self._configuration

    @configuration.setter
    def configuration(self, configuration):
        self._configuration = configuration

    def load_data_sets(self, sources):
        data_sets = {}

        # Check for multiple definitions of sets
        seen = []
        for ds_def in self._configuration:
            if ds_def['name'] not in seen:
                seen.append(ds_def['name'])
            else:
                raise YaaniError(
                    "The data set '{}' is defined twice.\n"
                    .format(ds_def['name'])
                )

        # Instantiate every data sets
        for ds_def in self._configuration:
            # Extract variables
            ds_strat = ds_def['from']
            ds_args = ds_def['args']
            ds_name = ds_def['name']

            strategy = ds_strat

            if strategy == DataSetLoader.STRATEGY.SOURCE:
                m = {
                    NetboxSource: DataSetLoader.STRATEGY.NETBOX_SOURCE,
                    FileSource: DataSetLoader.STRATEGY.FILE_SOURCE,
                    ScriptSource: DataSetLoader.STRATEGY.FILE_SOURCE
                }
                try:
                    src_name = ds_args['name']
                except KeyError as err:
                    raise YaaniError(
                        "Missing key '{}' in data sets '{}' creation "
                        "arguments.\n"
                        .format(err.args[0], ds_name)
                    )
                try:
                    strategy = m[type(sources.get(src_name))]
                except KeyError as err:
                    raise YaaniError(
                        "The source name '{}' refers to an undeclared "
                        "source. Please make sure this source is "
                        "declared in the 'data_sources' section."
                        .format(src_name)
                    )
            # Validate data set arguments
            Validator.DataSets.validate_data_set_args(
                strategy,
                ds_args
            )

            # Actually create the data set and place it in the proper place
            try:
                data_sets[ds_name] = DataSetLoader.Utils.create_set(
                    strategy=ds_strat,
                    args=ds_args,
                    sources=sources,
                    data_sets=data_sets
                )
            except YaaniError as err:
                raise YaaniError(
                    "Could not create data set '{}':\n{}"
                    .format(ds_name, str(err))
                )

        return data_sets


class InventoryRenderer:
    """Inventory Builder is the object that builds and return the inventory.
    """
    class Utils:
        @staticmethod
        def init_inventory():
            return {'_meta': {'hostvars': {}}}

        @staticmethod
        def apply_condition(cnd_value, elt_list, rndrd_ns=False):
            tmp_dct = {id(elt): elt for elt in elt_list}
            query = "[ .[] | select(.[1]{}) | .[0] ]".format(cnd_value)

            if rndrd_ns:
                tstd_lst = [(uid, elt[1]) for uid, elt in tmp_dct.items()]
            else:
                tstd_lst = [(uid, elt[0]) for uid, elt in tmp_dct.items()]

            try:
                mtchng_ids = pyjq.first(
                    query,
                    tstd_lst
                )
            except ValueError as err:
                raise YaaniError(
                    "The given query '{}' seems to be incorrect.\n"
                    .format(cnd_value)
                )
            cntnt = [tmp_dct[k] for k in mtchng_ids]

            return cntnt

        @staticmethod
        def render_host_vars(config, data_set):
            tmp_dct = {
                id(elt): elt for elt in data_set
            }

            # If no vars were specified, render all host vars
            if len(config) == 0:
                query = "[ .[] | [.[0], (.[1]) ] ]"
            else:
                acc = ""
                for var, vardf in config.items():
                    acc += "{}: ({}), ".format(var, vardf)
                acc = acc[:-2]
                query = "[ .[] | [.[0], (.[1] | {%s}) ]]" % (acc)

            try:
                comptd = pyjq.first(
                    query,
                    [(uid, elt[0]) for uid, elt in tmp_dct.items()]
                )
            except ValueError as err:
                raise YaaniError(
                    "One of the given query seems to be incorrect: {}\n"
                    .format(list(config.values()))
                )

            try:
                for uid, rndrd in [tuple(e) for e in comptd]:
                    tmp_dct[uid][1].update(rndrd)
            except ValueError as err:
                raise YaaniError(
                    "Host vars rendering failed. {}\n"
                    "This may happen when rendering lists in host vars. "
                    "If one of the expected values is a list, don't forget "
                    "to use the jq list constructor operator '[]' as "
                    "unfolding a list with .[] produce parallel results.\n"
                    "Example:\n\t.elt_list[].id -> [.elt_list[].id]"
                    .format(str(err))
                )
            return data_set

        @staticmethod
        def index_elements(index_cfg, data_set):
            # Compute index list
            tmp_dct = {
                id(elt): elt for elt in data_set
            }

            if index_cfg.get("namespace", "import") == "build":
                i = 1
            else:
                i = 0

            try:
                value = index_cfg["value"]
            except KeyError:
                raise YaaniError(
                    "The 'value' key is mandatory in index config.\n"
                )

            try:
                mpng_uid_indx = pyjq.first(
                    "[ .[] | [.[0], (.[1]{})] ]".format(value),
                    [
                        (uid, elt[i])
                        for uid, elt in tmp_dct.items()
                    ]
                )
            except ValueError as err:
                raise YaaniError(
                    "The given query '{}' seems to be incorrect.\n"
                    .format(value)
                )

            result = {}
            for uid, indx in map(lambda x: tuple(x), mpng_uid_indx):
                if indx:
                    if isinstance(indx, list) or isinstance(indx, dict):
                        raise YaaniError(
                            "Element indexing failed with query '{}'.\n"
                            "A container (list or dict) cannot be used as "
                            "an index: {}"
                            .format(index_cfg["value"], indx)
                        )
                    if indx in result:
                        raise YaaniError(
                            "Element indexing failed with query '{}'.\n"
                            "Two elements ended up with the same index: {}."
                            .format(index_cfg["value"], indx)
                        )
                    else:
                        result[indx] = tmp_dct[uid]

            return result

        @staticmethod
        def render_group(rdr_opts, data_sets, inventory):
            ds_name = rdr_opts["name"]
            try:
                ds_content = data_sets[ds_name]
            except KeyError as err:
                raise YaaniError(
                    "'{}' refers to an unexisting data set."
                    .format(ds_name)
                )

            rdr_pre_cdtn = rdr_opts["args"].get('pre_condition')
            rdr_post_cdtn = rdr_opts["args"].get('post_condition')
            rdr_host_vars = rdr_opts["args"].get('host_vars', {})

            # Associate elt with future rendered dict as tuples
            cntnt = [(elt, {}) for elt in ds_content]

            # Apply pre condition
            try:
                if rdr_pre_cdtn:
                    cntnt = InventoryRenderer.Utils.apply_condition(
                        rdr_pre_cdtn,
                        cntnt
                    )
            except YaaniError as err:
                raise YaaniError(
                    "Could not apply pre condition.\n{}".format(str(err))
                )

            # Load hostvars in every object
            try:
                cntnt = InventoryRenderer.Utils.render_host_vars(
                    rdr_host_vars,
                    cntnt
                )
            except YaaniError as err:
                raise YaaniError(
                    "Could not render host vars.\n{}".format(str(err))
                )

            # Apply post condition
            try:
                if rdr_post_cdtn:
                    cntnt = InventoryRenderer.Utils.apply_condition(
                        rdr_post_cdtn['value'],
                        cntnt,
                        rdr_post_cdtn.get('namespace', "import") == "build"
                    )
            except YaaniError as err:
                raise YaaniError(
                    "Could not apply post condition.\n{}".format(str(err))
                )

            try:
                indxd = InventoryRenderer.Utils.index_elements(
                    rdr_opts["args"]["index"], cntnt
                )
            except YaaniError as err:
                raise YaaniError(
                    "Could not index elements in data set '{}'.\n{}"
                    .format(ds_name, str(err))
                )

            # Insert every elements of the group in the inventory
            for idx, elt in indxd.items():
                # Compute an index for the given host data
                # elt = dict(elt_content)
                InventoryRenderer.Utils.add_element_to_inventory(
                    elt_idx=idx,
                    elt=elt,
                    ds_name=ds_name,
                    inventory=inventory,
                    rdr_opts=rdr_opts,
                )

            # Execute group_by
            rdr_group_by = rdr_opts["args"].get('group_by', None)
            rdr_group_prefix = rdr_opts["args"].get('group_prefix', "")

            try:
                InventoryRenderer.Utils.render_group_by(
                    indexed_data_set=indxd,
                    group_by=rdr_group_by,
                    group_prefix=rdr_group_prefix,
                    inventory=inventory
                )
            except YaaniError as err:
                raise YaaniError(
                    "Could not execute grouping feature.\n{}".format(str(err))
                )

        @staticmethod
        def add_element_to_inventory(elt_idx, elt, ds_name,
                                     inventory, rdr_opts={}):
            # Load the host vars in the inventory
            InventoryRenderer.Utils.load_element_vars(
                element_index=elt_idx,
                element=elt,
                inventory=inventory
            )
            # Add the host to its group and to the group 'all'
            InventoryRenderer.Utils.add_element_to_group(
                element_name=elt_idx,
                group_name=ds_name,
                inventory=inventory
            )
            InventoryRenderer.Utils.add_element_to_group(
                element_name=elt_idx,
                group_name='all',
                inventory=inventory
            )

        @staticmethod
        def load_element_vars(element_index, element, inventory):
            # Add the loaded variables in the inventory under the proper
            # section (name of the host)
            inventory['_meta']['hostvars'].update(
                {element_index: element[1]}
            )

        @staticmethod
        def render_group_by(indexed_data_set, group_by, group_prefix,
                            inventory):
            # If the group_by option is specified, insert the element in the
            # propper groups.
            if group_by:
                # Build the query
                acc = ""
                for grp_def in group_by:
                    if grp_def.get("namespace", "import") == "build":
                        index = 1
                    else:
                        index = 0
                    acc += "(.[{}]{}), ".format(index, grp_def["value"])
                acc = acc[:-2]
                query = "[ .[] | [.[0], (.[1] | [{}] | flatten)]]".format(acc)
                # Extract the mapping uid / [groups]
                try:
                    mpng = pyjq.first(
                        query,
                        list(indexed_data_set.items())
                    )
                except ValueError as err:
                    raise YaaniError(
                        "One of the given query seems to be incorrect: {}\n"
                        .format([e["value"] for e in group_by])
                    )

                # Execute grouping
                for indx, groups in mpng:
                    for group in groups:
                        if group is not None:
                            InventoryRenderer.Utils.add_element_to_group(
                                element_name=indx,
                                group_name=group_prefix + str(group),
                                inventory=inventory
                            )

            return inventory

        @staticmethod
        def add_element_to_group(element_name, group_name, inventory):
            inventory = InventoryRenderer.Utils.init_ansible_group(
                group_name=group_name,
                inventory=inventory
            )
            if (
                element_name not in
                inventory.get(group_name, {}).get('hosts', [])
            ):
                inventory[group_name]['hosts'].append(element_name)
            return inventory

        @staticmethod
        def init_ansible_group(group_name, inventory):
            # Initialize the group in the inventory
            inventory.setdefault(group_name, {})
            # Initialize the host field of the group
            inventory[group_name].setdefault('hosts', [])
            inventory[group_name].setdefault('vars', {})
            inventory[group_name].setdefault('children', [])
            return inventory

        @staticmethod
        def load_group_vars(group_name, data, inventory):
            InventoryRenderer.Utils.init_ansible_group(group_name, inventory)

            inventory[group_name]['vars'] = data

            return inventory

        @staticmethod
        def load_group_hierarchy(hierarchy, inventory):
            for parent, children in hierarchy.items():
                InventoryRenderer.Utils.init_ansible_group(parent, inventory)
                if isinstance(children, dict):
                    inventory[parent]['children'] = list(children.keys())
                    InventoryRenderer.Utils.load_group_hierarchy(
                        children,
                        inventory
                    )
            return inventory

    def __init__(self, script_args, render_config):
        # Script args
        self._config_file = script_args['config_file']
        self._host = script_args['host']
        self._list_mode = script_args['list']

        # Configuration file
        self._configuration = render_config

    def render_inventory(self, data_sets):
        inventory = InventoryRenderer.Utils.init_inventory()

        if self._list_mode:
            # Start rendering
            for rdr_opts in self._configuration["elements"]:
                # Check for undefined data-set name
                name = rdr_opts['name']
                if name not in data_sets:
                    raise YaaniError(
                        "The data set to render '{}' does not exist."
                        .format(name)
                    )
                try:
                    InventoryRenderer.Utils.render_group(
                        rdr_opts=rdr_opts,
                        data_sets=data_sets,
                        inventory=inventory
                    )
                except YaaniError as err:
                    raise YaaniError(
                        "Could not render data set '{}':\n{}"
                        .format(rdr_opts['name'], str(err))
                    )

            for grp_var_def in self._configuration.get("group_vars", []):
                try:
                    group_name = grp_var_def['group']
                    set_name = grp_var_def['set']
                except KeyError as err:
                    raise YaaniError(
                        "The '{}' key is mandatory in group vars definition.\n"
                        .format(err.args[0])
                    )

                try:
                    data_set = data_sets[set_name]
                except KeyError as err:
                    raise YaaniError(
                        "The required set '{}' is not known.\n"
                        .format(err.args[0])
                    )

                InventoryRenderer.Utils.load_group_vars(
                    group_name=group_name,
                    data=data_set,
                    inventory=inventory
                )

            InventoryRenderer.Utils.load_group_hierarchy(
                hierarchy=self._configuration.get("group_hierarchy", {}),
                inventory=inventory
            )

        return inventory

# ****************************************************************************
# *                                DataSources                               *
# ****************************************************************************


class DataSource(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def extract(self, args):
        pass


class FullSetSource(DataSource):
    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def filter(self, *args, **kwargs):
        pass


class PartialSetSource(DataSource):
    pass


class TextSource(FullSetSource):
    def __init__(self, args):
        self._path = args['path']
        self._content_type = args['content_type']
        if self._content_type.lower() == 'yaml':
            self._loading_method = yaml.safe_load
            self._dumping_method = yaml.dump
        elif self._content_type.lower() == 'json':
            self._loading_method = json.load
            self._dumping_method = json.dumps
        else:
            raise YaaniError(
                "The content type '{}' is not supported.\n"
                .format(self._content_type)
            )

        self._dataset = self.load()

    def __repr__(self):
        return "<{} source from {}>".format(
            self._content_type.upper(),
            self._path
        )

    def __str__(self):
        return self._dumping_method(self._dataset)

    def load(self):
        try:
            with open(self._path, 'r') as file:
                data = self._loading_method(file)
        except IOError as err:
            # Handle file level exception
            raise YaaniError(
                "The specified file could not be opened: {}.\n{}\n"
                .format(self._path, str(err))
            )
        except yaml.YAMLError as yaml_error:
            raise YaaniError(
                "There was an error during the parsing of '{}'.\n{}\n"
                .format(self._path, yaml_error)
            )
        except json.decoder.JSONDecodeError as json_error:
            raise YaaniError(
                "There was an error during the parsing of '{}'.\n{}\n"
                .format(self._path, json_error)
            )

        return data

    def filter(self, query):
        try:
            return pyjq.all(query, self._dataset)
        except ValueError as err:
            raise YaaniError(
                "Jq could not compile the following query: {}\n{}\n"
                .format(query, str(err))
            )

    def extract(self, args):
        try:
            return self.filter(args['filter'])
        except KeyError as err:
            raise YaaniError(
                "Data extraction failed due to missing key '{}'.\n"
                .format(err.args[0])
            )


class FileSource(TextSource):
    pass


class ScriptSource(TextSource):
    def __init__(self, args):
        self._path = args['path']
        self._content_type = args['content_type']
        if self._content_type.lower() == 'yaml':
            self._loading_method = yaml.safe_load
            self._dumping_method = yaml.dump
        elif self._content_type.lower() == 'json':
            self._loading_method = json.loads
            self._dumping_method = json.dumps
        else:
            raise YaaniError(
                "The content type '{}' is not supported.\n"
                .format(self._content_type)
            )

        self._dataset = self.load()

    def load(self):
        try:
            import subprocess

            p = subprocess.run(
                "{}".format(self._path),
                stdout=subprocess.PIPE,
            )

            data = self._loading_method(p.stdout)
        except IOError as err:
            # Handle file level exception
            raise YaaniError(
                "The specified file could not be executed: {}\n{}\n"
                .format(self._path, str(err))
            )
        except yaml.YAMLError as yaml_error:
            raise YaaniError(
                "There was an error during the parsing of '{}'.\n{}\n"
                .format(self._path, yaml_error)
            )
        except json.decoder.JSONDecodeError as json_error:
            raise YaaniError(
                "There was an error during the parsing of '{}'.\n{}\n"
                .format(self._path, json_error)
            )

        return data


class NetboxSource(PartialSetSource):
    def __init__(self, args):
        self._api = pynetbox.api(**args)

    def extract(self, args):
        try:
            nb_app = args["app"].lower().replace("-", "_")
            nb_type = args["type"].lower().replace("-", "_")
        except KeyError as err:
            raise YaaniError(
                "The netbox source arguments are incomplete. "
                "Missing key '{}'.\n"
                .format(err.args[0])
            )

        endpoint = getattr(getattr(self._api, nb_app), nb_type)

        collection = []
        try:
            if "filters" in args:
                seen_id = []
                for filter_args in args['filters']:
                    for elt in endpoint.filter(**filter_args):
                        # Add the element to collection only if it is not
                        # already in
                        if elt.id not in seen_id:
                            seen_id.append(elt.id)
                            collection.append(dict(elt))
            else:
                collection = [dict(e) for e in endpoint.all()]
        except pynetbox.core.query.RequestError as err:
            raise YaaniError(
                "An error occured while requesting Netbox: {}\n"
                .format(str(err))
            )
        except requests.exceptions.ConnectionError as err:
            raise YaaniError(
                "An error occured while requesting Netbox: {}\n"
                .format(str(err))
            )
        return collection


class Utils:
    @staticmethod
    def exit(error, code):
        """Write an error message on stderr and exit the program with the
        given return code.

        Args:
            error (str): The message
            code (int): The return code

        """
        sys.stderr.write(str(error))
        sys.exit(code)

    @staticmethod
    def parse_cli_args(script_args):
        """Declare and configure script argument parser

        Args:
                script_args (list): The list of script arguments

        Returns:
                obj: The parsed arguments in an object.
                     See argparse documention
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
                    default value is %s environment variable or netbox.yml
                    in the current dir.""" % DEFAULT_ENV_CONFIG_FILE
        )
        parser.add_argument(
            '--list', action='store_true', default=False,
            help="""Print the entire inventory with hostvars respecting
                    the Ansible dynamic inventory syntax."""
        )
        parser.add_argument(
            '--host', action='store', default=None,
            help="""Return an empty inventory."""
        )

        # Parse script arguments and return the result
        return parser.parse_args(script_args)

    @staticmethod
    def load_config_file(config_file_path):
        """Load the configuration file and returns its parsed content.

        Args:
            config_file_path (str): The path towards the configuration file
        """
        try:
            with open(config_file_path, 'r') as file:
                parsed_config = yaml.safe_load(file)
        except IOError:
            # Handle file level exception
            raise YaaniError(
                "The configuration file could not be found: {}"
                .format(config_file_path)
            )
        except yaml.YAMLError as yaml_error:
            raise YaaniError(
                "There was an error during the parsing of the configuration "
                "file.\n{}\n{}\n"
                .format(config_file_path, str(yaml_error))
            )

        return parsed_config

    @staticmethod
    def dump_json_inventory(inventory):
        """Dumps the given inventory in json

        Args:
                inventory (dict): The inventory
        """
        print(json.dumps(inventory))

    @staticmethod
    def transform_inventory(render_configuration, inventory):
        """If a transformation configuration exists, execute users functions.
        Dumps the inventory in JSON format to the standard output.

        Args:
            render_configuration (list): The transformation configuration
            inventory (dict): The inventory
        """
        if render_configuration:
            func_array = []
            for fdef in render_configuration:
                try:
                    custom_module_name = fdef['module']
                    func_name = fdef['func']
                except KeyError as err:
                    raise YaaniError(
                        "The custom transformation failed due to missing "
                        "keys in the configuration: {}\n"
                        .format(err.args[0])
                    )

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
                except ImportError as err:
                    raise YaaniError(
                        "The import of the custome module '{}' failed.\n"
                        "{}"
                        .format(custom_module_name, str(err))
                    )
                except FileNotFoundError as err:
                    raise YaaniError(
                        "The import of the custome module '{}' failed.\n"
                        "{}"
                        .format(custom_module_name, str(err))
                    )

                try:
                    custom_func = getattr(custom_module, func_name)
                except AttributeError as err:
                    raise YaaniError(
                        "The function '{}' could not be found:\n{}\n"
                        .format(func_name, str(err))
                    )

                func_array.append(custom_func)

            for f in func_array:
                inventory = f(inventory)

        # Dump inventory
        Utils.dump_json_inventory(inventory)


def cli(cli_argv):
    # Parse cli args
    args = vars(Utils.parse_cli_args(cli_argv[1:]))
    # Parse and validate the configuration file
    try:
        configuration = Utils.load_config_file(args['config_file'])
    except YaaniError as err:
        Utils.exit(err, 6)
    # Configuration structure validation
    try:
        try:
            Validator.DataSources.validate_configuration(
                configuration["data_sources"]
            )
            Validator.DataSets.validate_configuration(
                configuration["data_sets"]
            )
            Validator.Render.validate_configuration(
                configuration["render"]
            )
            Validator.Transform.validate_configuration(
                configuration.get("transform", [])
            )
        except KeyError as err:
            raise YaaniError(
                "The '{}' key is missing from the configuration file."
                .format(err.args[0])
            )
    except YaaniError as err:
        Utils.exit(err, 1)

    # Load data sources ------------------------------------------------------
    try:
        src_ldr = SourceLoader(configuration=configuration["data_sources"])
        sources = src_ldr.load_sources()
        if len(sources) == 0:
            raise YaaniError(
                "No source has been loaded. Cannot render anything "
                "without data."
            )
    except YaaniError as err:
        Utils.exit(err, 2)

    # Load data_sets ---------------------------------------------------------
    try:
        ds_ldr = DataSetLoader(configuration=configuration["data_sets"])
        data_sets = ds_ldr.load_data_sets(sources)
        if len(sources) == 0:
            raise YaaniError(
                "No data set has been loaded. Cannot render anything "
                "without data."
            )
    except YaaniError as err:
        Utils.exit(err, 3)

    # Render the inventory ---------------------------------------------------
    try:
        renderer = InventoryRenderer(
            script_args=args,
            render_config=configuration["render"]
        )
        # Actual inventory rendering
        inventory = renderer.render_inventory(
            data_sets=data_sets
        )
    except YaaniError as err:
        Utils.exit(err, 4)

    try:
        # Print the JSON formatted inventory dict
        transformer = Utils.transform_inventory(
            configuration.get('transform', []),
            inventory
        )
    except YaaniError as err:
        Utils.exit(err, 5)


if __name__ == '__main__':
    cli(sys.argv)
