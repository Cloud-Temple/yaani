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
