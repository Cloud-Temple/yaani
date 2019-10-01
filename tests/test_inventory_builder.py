import pytest

from yaani import (
    InventoryBuilder
)


@pytest.fixture
def cli_args():
    """Return simple argument set coherent with InventoryBuilder"""

    class Args:
        def __init__(self):
            self.config_file = "netbox.yml"
            self.host = None
            self.list = True

    return Args()


@pytest.fixture
def namespaces():
    return {
        "build": {
            "b1": "bv1",
            "b2": "bv2",
            "b3": "bv3",
            "b4": [
                "a",
                "b",
                "c"
            ],
            "b5": {
                "bk1": "bkv1",
                "bk2": "bkv2",
            }
        },
        "import": {
            "i1": "iv1",
            "i2": "iv2",
            "i3": "iv3",
            "i4": [
                "a",
                "b",
                "c"
            ],
            "i5": {
                "ik1": "ikv1",
                "ik2": "ikv2",
            }
        },
        "sub-import": {
            "s1": "sv1",
            "s2": "sv2",
            "s3": "sv3",
            "s4": [
                "a",
                "b",
                "c"
            ],
            "s5": {
                "sk1": "skv1",
                "sk2": "skv2",
            }
        }
    }


@pytest.fixture
def config():
    """Return simple argument set coherent with InventoryBuilder"""
    conf = {
        "netbox": {
            "api": {
                "url": "url test"
            },
            "import": {
                "devices": {
                    "filters": {
                        "role_id": 20
                    }
                }
            }
        }
    }
    return conf


@pytest.fixture
def device_import_option():
    return InventoryBuilder(cli_args, config).imports.get('dcim', {}).get('devices', {})


@pytest.fixture
def init_inventory():
    return {"_meta": {"hostvars": {}}}
    # return {
    #     "_meta": {"hostvars": {}},
    #     "devices": {"hosts": []},
    #     "all": {"hosts": []},
    #     "dev_cpe": {"hosts": []}
    # }

    # return {
    #     "_meta": {"hostvars": {}},
    #     "devices": {"hosts": ["BK A07-0", "BK A07-1"]},
    #     "all": {"hosts": ["BK A07-0", "BK A07-1"]},
    #     "dev_cpe": {"hosts": ["amf-1.cpe0009", "asi-1.cpe0001"]}
    # }


@pytest.fixture
def inv_builder(cli_args, config):
    return InventoryBuilder(cli_args, config)


@pytest.mark.parametrize("group,inventory,expected", [
    (  # non existing group
        "test_group",
        {},
        {
            "test_group": {
                "hosts": []
            }
        }
    ),
    (  # existing group with no hosts
        "test_group",
        {
            "test_group": {
                "test_key": "1"
            }
        },
        {
            "test_group": {
                "test_key": "1",
                "hosts": []
            }
        }
    ),
    (  # existing group with hosts
        "test_group",
        {
            "test_group": {
                "hosts": [
                    1,
                    2
                ]
            }
        },
        {
            "test_group": {
                "hosts": [
                    1,
                    2
                ]
            }
        }
    ),
])
def test_initialize_group(inv_builder, group, inventory, expected):
    """Test the _initialize_group method properly works"""
    assert inv_builder._initialize_group(group, inventory) == expected


@pytest.mark.parametrize("host,obj_type,expected", [
    (  # present name
        {
            "id": 1,
            "name": "test_name"
        },
        "device",
        "test_name"
    ),
    (  # absent name, present id
        {
            "id": 1,
        },
        "device",
        "device_1"
    ),
])
def test_get_identifier_ok(inv_builder, host, obj_type, expected):
    """Test the get_identifier method properly works"""
    assert inv_builder._get_identifier(host, obj_type) == expected


@pytest.mark.parametrize("host,obj_type", [
    (  # absent name, present id
        {},
        "device"
    ),
])
def test_get_identifier_ko(inv_builder, host, obj_type):
    """Test the get_identifier method raises an error when it should"""
    with pytest.raises(SystemExit) as err:
        inv_builder._get_identifier(host, obj_type)
    assert "The id key is not present" in str(err.value)


@pytest.mark.parametrize("element_name,group_name,inventory,expected", [
    (  # Existing group with already existing element
        "item1",
        "group1",
        {
            "group1": {
                "hosts": [
                    "item1"
                ]
            }
        },
        {
            "group1": {
                "hosts": [
                    "item1"
                ]
            }
        }
    ),
    (  # Existing group with non existing element
        "item1",
        "group1",
        {
            "group1": {
                "hosts": [
                    "item2"
                ]
            }
        },
        {
            "group1": {
                "hosts": [
                    "item2",
                    "item1"
                ]
            }
        }
    ),
    (  # Non existing group with non existing element
        "item1",
        "group1",
        {
            "group2": {
                "hosts": [
                    "item2"
                ]
            }
        },
        {
            "group2": {
                "hosts": [
                    "item2"
                ]
            },
            "group1": {
                "hosts": [
                    "item1"
                ]
            },
        }
    ),
])
def test_add_element_to_group(inv_builder, element_name,
                              group_name, inventory, expected):
    assert inv_builder._add_element_to_group(
        element_name, group_name, inventory
    ) == expected


@pytest.mark.parametrize("key_path,expected", [
    (  # single item of import section (default section)
        ".i1",
        "iv1"
    ),
    (  # single item of import section (unknown namespace)
        "a#.i1",
        "iv1"
    ),
    (  # single item of import section
        "i#.i1",
        "iv1"
    ),
    (  # single item of import section in list
        "il#.i1",
        ["iv1"]
    ),
    (  # list items of import section
        "i#.i4",
        ["a", "b", "c"]
    ),
    (  # unfolded list of import section
        "il#.i4[]",
        ["a", "b", "c"]
    ),
    (  # unfolded list of import section first element
        "i#.i4[]",
        "a"
    ),
    (  # dict of import section
        "i#.i5",
        {
            "ik1": "ikv1",
            "ik2": "ikv2"
        }
    ),
    (  # dict of import section in a list
        "il#.i5",
        [{
            "ik1": "ikv1",
            "ik2": "ikv2"
        }]
    ),
    (  # unfolded dict of import section as a list
        "il#.i5[]",
        [
            "ikv1",
            "ikv2"
        ]
    ),
    (  # single item of build section
        "b#.b1",
        "bv1"
    ),
    (  # single item of build section in list
        "bl#.b1",
        ["bv1"]
    ),
    (  # list items of build section
        "b#.b4",
        ["a", "b", "c"]
    ),
    (  # unfolded list of build section
        "bl#.b4[]",
        ["a", "b", "c"]
    ),
    (  # unfolded list of build section first element
        "b#.b4[]",
        "a"
    ),
    (  # dict of build section
        "b#.b5",
        {
            "bk1": "bkv1",
            "bk2": "bkv2"
        }
    ),
    (  # dict of build section in a list
        "bl#.b5",
        [{
            "bk1": "bkv1",
            "bk2": "bkv2"
        }]
    ),
    (  # # unfolded dict of build section as a list
        "bl#.b5[]",
        [
            "bkv1",
            "bkv2"
        ]
    ),
    (  # single item of sub-import section
        "s#.s1",
        "sv1"
    ),
    (  # single item of sub-import section in list
        "sl#.s1",
        ["sv1"]
    ),
    (  # list items of sub-import section
        "s#.s4",
        ["a", "b", "c"]
    ),
    (  # unfolded list of sub-import section
        "sl#.s4[]",
        ["a", "b", "c"]
    ),
    (  # unfolded list of sub-import section first element
        "s#.s4[]",
        "a"
    ),
    (  # dict of sub-import section
        "s#.s5",
        {
            "sk1": "skv1",
            "sk2": "skv2"
        }
    ),
    (  # dict of sub-import section in a list
        "sl#.s5",
        [{
            "sk1": "skv1",
            "sk2": "skv2"
        }]
    ),
    (  # unfolded dict of sub-import section as a list
        "sl#.s5[]",
        [
            "skv1",
            "skv2"
        ]
    ),
])
def test_resolve_expression(inv_builder, namespaces, key_path, expected):
    assert inv_builder._resolve_expression(key_path, namespaces) == expected


@pytest.fixture
def test_data():
    return {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": None,
        "e": {
            "e_a": "test value"
        }
    }


@pytest.mark.parametrize("arg, exp", [
    ("a", 1),  # regular key
    ("b", 2),  # regular key
    ("c", 3),  # regular key
    ("d", None),  # regular key with None value
    ("e", {"e_a": "test value"}),  # regular key with dict value
    ("e.e_a", "test value"),  # key in a dict
    ("a | default_key(b)", 1),  # default_key test on non null value
    ("d | default_key(b)", 2),  # default_key test on null value
    ("e.e_a | sub(\"value\",\"\")", "test "),  # sub on non null value
    # sub on non null value with optional occurence count
    ("e.e_a | sub(\"e\",\"\", 1)", "tst value"),
    # sub on non null value with optional occurence count
    ("e.e_a | sub(\"e$\",\"\", 1)", "test valu"),
    ("d | sub(\"value\",\"\")", None),  # sub non null value
])
def test_expr_reso_grammar_ok(inv_builder, test_data, arg, exp):
    p = inv_builder.parser

    t = Transformer(data=test_data)
    assert t.transform(p.parse(arg)) == exp


@pytest.mark.parametrize("args", [
    ({  # config file plus list
        "config-file": "netbox.yml",
        "list": True,
        "host": None,
    }),
    ({  # no list, plus host
        "config-file": "netbox.yml",
        "list": False,
        "host": "hostname",
    }),
    ({  # list alone, no host, no config file
        "config-file": "netbox.yml",
        "list": True,
        "host": None,
    }),
    ({  # list alone, no host, no config file
        "config-file": "netbox.yml",
        "list": False,
        "host": None,
    }),
])
def test_init_builder_ok(args, config):
    class Args:
        def __init__(self):
            self.config_file = args['config-file']
            self.host = args['host']
            self.list = args['list']

    builder = InventoryBuilder(Args(), config)

    assert builder.config_file == args['config-file']
    assert builder.list_mode == args['list']
    assert builder.host == args['host']


@pytest.mark.parametrize("element_name, application, import_type, hostvalue", [
    (
        "BK A07-0",
        "dcim",
        "devices",
        "hostvalue"
    ),
    (
        "amf-1.cpe0009",
        "dcim",
        "devices",
        ""
    ),
    (
        "BK A07-0",
        "dcim",
        "devices",
        None
    ),
])
def test_add_element_to_inventory_ok(cli_args, config, element_name, application,
                                     import_type, hostvalue):
    import_options = InventoryBuilder(cli_args, config).imports.get(application, {})
    inventory = {"_meta": {"hostvars": {}}}
    assert InventoryBuilder._add_element_to_inventory(
        InventoryBuilder(cli_args, config),
        element_name,
        dict(name=hostvalue),
        inventory,
        import_type,
        import_options.get('group_by', None),
        import_options.get('group_prefix', None),
        import_options.get('host_vars', None)
    ) is None


@pytest.mark.parametrize("application, import_type", [
    (
        "dcim",
        "devices",
    ),
])
def test_execute_import_ok(cli_args, config, application, import_type):
    import_options = InventoryBuilder(cli_args, config).imports.get(application,
                                                                    {}).get(import_type, {})
    inventory = {"_meta": {"hostvars": {}}}
    assert InventoryBuilder._execute_import(
        InventoryBuilder(cli_args, config),
        application,
        import_type,
        import_options,
        inventory
    ) is None


@pytest.mark.parametrize("application, import_type", [
    (
        "dcim",
        "devices",
    ),
])
def test_get_element_list_ok(cli_args, config, application, import_type):
    invbuil = InventoryBuilder(cli_args, config)
    filters = invbuil.imports.get(application, {}).get(import_type, {}).get('filters', None)
    assert InventoryBuilder._get_elements_list(
        invbuil,
        application,
        import_type,
        filters=filters,
        specific_host=invbuil.host
    )
