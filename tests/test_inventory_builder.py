import pytest

from yaani import InventoryBuilder
from yaani import Transformer


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
                "api_url": "url test"
            },
            "import": {
                "devices": {
                    "filter": "test"
                }
            }
        }
    }

    return conf


@pytest.fixture
def inv_builder(cli_args, config):
    return InventoryBuilder(cli_args, config)

