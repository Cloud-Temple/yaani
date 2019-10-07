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
