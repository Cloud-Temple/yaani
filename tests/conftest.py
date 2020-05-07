import pytest
from yaani.yaani import (
    SourceLoader,
    DataSetLoader,
    InventoryRenderer
)


@pytest.fixture
def cli_args():
    """Return simple argument set coherent with InventoryBuilder"""
    class Args:
        def __init__(self):
            self.config_file = "netbox.yml"
            self.host = None
            self.list = True

    return vars(Args())


@pytest.fixture
def i_dselt():
    return DataSetElement._DataSetElement()


@pytest.fixture
def ds_ldr():
    return DataSetLoader()


@pytest.fixture
def src_ldr():
    return SourceLoader()


@pytest.fixture
def inv_rdr():
    return InventoryRenderer()


@pytest.fixture
def ds_elt():
    return DataSetElement()
