import pytest
import mock

from yaani.yaani import (
    InventoryBuilder,
    resolve_expression)


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
                "dcim":{
                    "devices": {
                        "filters": {
                            "role_id": 20
                        },
                        "host_vars": [
                                {"b2": "item1"}
                        ],
                        "group_by": [
                                "i1",
                        ],
                        "group_prefix": "dev_",
                    }
                }
            },
        }
    }
    return conf


@pytest.fixture
def device_import_option():
    return InventoryBuilder(
            cli_args, config
        ).imports.get('dcim', {}).get('devices', {})


@pytest.fixture
def init_inventory():
    return {"_meta": {"hostvars": {}}}


@pytest.fixture
def inv_builder(cli_args, config):
    return InventoryBuilder(cli_args, config)


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
def test_resolve_expression_ok(inv_builder, namespaces, key_path, expected):
    assert inv_builder._resolve_expression(key_path, namespaces) == expected


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
    (  # Non existing group with existing element
        "item1",
        "group1",
        {
            "group2": {
                "hosts": [


                    "item1"
                ]
            }
        },
        {
            "group2": {
                "hosts": [
                    "item1"
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
def test_add_element_to_group_ok(inv_builder, element_name,
                                 group_name, inventory, expected):
    assert inv_builder._add_element_to_group(
        element_name,
        group_name,
        inventory
    ) == expected


@pytest.mark.parametrize(
    "element_name, inventory, namespace, group_by, "
    "group_prefix, expected",
    [
        (
            "item1",
            {"_meta": {"hostvars": {}}},
            {"import": {"i1": "iv1", "i2": "iv2"}},
            {'.i1', '.i2'},
            "dev_",
            {'_meta': {'hostvars': {}},
             'dev_iv2': {'hosts': ['item1']},
             'dev_iv1': {'hosts': ['item1']}},
        ),
        (
            "item2",
            {"_meta": {"hostvars": {}}},
            {"import": {"i2": "iv2", "i3": "iv3"}},
            {'.i3'},
            "",
            {'_meta': {'hostvars': {}},
             'iv3': {'hosts': ['item2']}},
        ),
        (
            "item3",
            {"_meta": {"hostvars": {'item0': {'b0': 'bv0'}}}},
            {"import": {"i1": "iv1", "i2": 0, "i3": "iv3"}},
            {'.i2'},
            None,
            {'_meta': {'hostvars': {'item0': {'b0': 'bv0'}}},
             0: {'hosts': ['item3']}},
        ),
        (
            "item4",
            {"_meta": {"hostvars": {'item0': {'b0': 'bv0'}}}},
            {"import": {"i1": "iv1", "i2": None, "i3": "iv3"}},
            {'.i2'},
            "",
            {'_meta': {'hostvars': {'item0': {'b0': 'bv0'}}}},
        ),
        (
            "item5",
            {"_meta": {"hostvars": {'item0': {'b0': 'bv0'}}}},
            {"import": {"i1": "iv1", "i2": "", "i3": "iv3"}},
            {'.i2'},
            "test_",
            {'_meta': {'hostvars': {'item0': {'b0': 'bv0'}}},
                'test_': {'hosts': ['item5']}},
        ),
    ]
)
def test_execute_group_by_ok(inv_builder, element_name, group_by,
                             group_prefix, namespace, inventory, expected):
    assert inv_builder._execute_group_by(
        element_index=element_name,
        group_by=group_by,
        group_prefix=group_prefix,
        inventory=inventory,
        namespaces=namespace
    ) is None
    assert inventory == expected


@pytest.mark.parametrize(
    "element_name, inventory, host_vars, namespace, expected",
    [
        (
            "item1",
            {"_meta": {"hostvars": {}}},
            [{'b1': 'b#.b2'}],
            {"build": {"b1": "bv1", "b2": "bv2"}, "import": {}},
            {'_meta': {'hostvars': {'item1': {'b1': 'bv2', 'b2': 'bv2'}}}},
        ),
        (
            "item2",
            {"_meta": {"hostvars": {}}},
            [{'b1': 'b#.b2'}],
            {"build": {"b1": "bv1", "b2": "bv2"}, "import": {}},
            {'_meta': {'hostvars': {'item2': {'b1': 'bv2', 'b2': 'bv2'}}}},
        ),
        (
            "item3",
            {"_meta": {"hostvars": {'item0': {'b0': 'bv0'}}}},
            [{'b2': 'b#.b1'}],
            {"build": {"b1": "bv1", "b2": "bv2"}, "import": {}},
            {'_meta': {'hostvars': {'item0': {'b0': 'bv0'},
                                    'item3': {'b1': 'bv1', 'b2': 'bv1'}}}},
        ),
        (
            "item4",
            {"_meta": {"hostvars": {'item0': {'b0': 'bv0'}}}},
            [{'b2': 'b#.b1'}],
            {"build": {"b1": "bv1", "b2": "bv2"}, "import": {}},
            {'_meta': {'hostvars': {'item0': {'b0': 'bv0'},
                                    'item4': {'b1': 'bv1', 'b2': 'bv1'}}}},
        ),
    ])
def test_load_element_vars_ok(element_name, inventory, host_vars,
                              namespace, expected, inv_builder):
    assert inv_builder._load_element_vars(
        element_name=element_name,
        inventory=inventory,
        host_vars=host_vars,
        namespaces=namespace
    ) is None
    assert inventory == expected


@pytest.mark.parametrize(
    "application,import_type,inventory,get_element_list,expected",
    [
        (
            "dcim",
            "racks",
            {"_meta": {"hostvars": {}}},
            [
                dict(id=1, name="item1"),
                dict(id=2, name="item2")
            ],
            {
                '_meta': {
                    'hostvars': {}
                },
                'devices': {
                    'hosts': [
                        'item1',
                        'item2'
                    ]
                },
                'all': {
                    'hosts': [
                        'item1',
                        'item2'
                    ]
                }
            }
        ),
        (
            "virtualization",
            "racks",
            {"_meta": {"hostvars": {}}},
            [
                dict(id=1, name="item1"),
                dict(id=2, name="item2"),
                dict(id=3, name="item3")
            ],
            {
                '_meta': {
                    'hostvars': {}
                },
                'racks': {
                    'hosts': [
                        'item1',
                        'item2',
                        'item3'
                    ]
                },
                'all': {
                    'hosts': [
                        'item1',
                        'item2',
                        'item3'
                    ]
                }
            }
        ),
        (
            "virtualization",
            "racks",
            {"_meta": {"hostvars": {}}},
            [
                dict(id=1, name="item1"),
                dict(id=2, name=""),
                dict(id=3, name=None)
            ],
            {
                '_meta': {
                    'hostvars': {}
                },
                'racks': {
                    'hosts': [
                        'item1',
                        '',
                        None
                    ]
                },
                'all': {
                    'hosts': [
                        'item1',
                        '',
                        None
                    ]
                }
            }
        ),
    ]
)
def test_execute_import_ok(inv_builder, application, inventory,
                           import_type, get_element_list, expected, mocker):
    import_options = inv_builder._import_section.get(application, {}).get(import_type, {})

    mocker.patch.object(
        InventoryBuilder,
        "_get_elements_list",
        return_value=get_element_list
    )

    assert inv_builder._execute_import(
        application=application,
        import_type=import_type,
        import_options=import_options,
        inventory=inventory
    ) is None


"""
@pytest.mark.parametrize("application, import_type", [
    (
        "dcim",
        "devices",
    ),
])
def test_get_element_list_ok(application, import_type, inv_builder):
    filters = inv_builder._import_section.get(application, {}).get(import_type, {}).get('filters', None)

    assert inv_builder._get_elements_list(
        application,
        import_type,
        filters=filters,
        specific_host=inv_builder._host
    )
    import_options = inv_builder._import_section.get(
        application, {}
    ).get(import_type, {})

    assert inv_builder._execute_import(
        application,
        import_type,
        import_options,
        inventory
    ) is None
    assert inventory == expected
"""
