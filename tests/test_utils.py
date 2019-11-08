import pytest

from yaani.yaani import (
    parse_cli_args,
    validate_configuration,
    resolve_expression
)
from jsonschema import ValidationError
import pytest
import pyjq


@pytest.fixture
def api_config():
    return {
        "url": "http://test.com"
    }


@pytest.fixture
def import_config():
    return {
        "dcim": {
            "devices": {
                "group_prefix": "_"
            }
        }
    }


@pytest.fixture
def test_data():
    return {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": None,
        "e": {
            "e_a": "test value"
        },
        "l": [
            "1",
            "2",
            "3"
        ],
        "l2": [
            {
                "a1": "b1"
            },
            {
                "a1": "b2"
            },
            {
                "a1": "b3"
            }
        ]
    }


@pytest.mark.parametrize("arg, first, exp", [
    # regular key
    (".a", False, [1]),
    # regular key
    (".b", False, [2]),
    # regular key
    (".c", False, [3]),
    # regular key with None value
    (".d", False, [None]),
    # regular key with dict value
    (".e", False, [{"e_a": "test value"}]),
    # key in a dict
    (".e.e_a", False, ["test value"]),
    # default_key test on non null value
    (".a // \"b\"", False, [1]),
    # default_key test on null value
    (".d // \"b\"", False, ["b"]),
    # sub on non null value
    (".e.e_a | sub(\"value\";\"\")", False, ["test "]),
    # sub non null value
    (".d // \"_\"| sub(\"value\";\"\")", False, ["_"]),
    # sub on list value
    (".l[] | sub(\"2\";\"\")", False, ["1", "", "3"]),
    # expand list
    (".l2[].a1", False, ["b1", "b2", "b3"]),
    # expand list and sub
    (".l2[].a1 | sub(\"b\"; \"c\")", False, ["c1", "c2", "c3"]),
    # regular key
    (".a", True, 1),
    # regular key
    (".b", True, 2),
    # regular key
    (".c", True, 3),
    # regular key with None value
    (".d", True, None),
    # regular key with dict value
    (".e", True, {"e_a": "test value"}),
    # key in a dict
    (".e.e_a", True, "test value"),
    # default_key test on non null value
    (".a // \"b\"", True, 1),
    # default_key test on null value
    (".d // \"b\"", True, "b"),
    # sub on non null value
    (".e.e_a | sub(\"value\";\"\")", True, "test "),
    # sub non null value
    (".d // \"_\"| sub(\"value\";\"\")", True, "_"),
    # sub on list value
    (".l[] | sub(\"2\";\"\")", True, "1"),
    # expand list
    (".l2[].a1", True, "b1"),
    # expand list and sub
    (".l2[].a1 | sub(\"b\"; \"c\")", True, "c1"),
])
def test_jqexpression_ok(test_data, arg, first, exp):
    """Test expression resolution through pyjq"""
    assert resolve_expression(arg, test_data, first) == exp


@pytest.mark.parametrize("args,exp", [
    (['-c', 'test.yml', '--list'], {  # config file plus list
        "config-file": "test.yml",
        "list": True,
        "host": None,
    }),
    (['--config-file', 'test.yml', '--list'], {  # config file long plus list
        "config-file": "test.yml",
        "list": True,
        "host": None,
    }),
    (['--host', 'hostname'], {  # no list, plus host
        "config-file": "netbox.yml",
        "list": False,
        "host": "hostname",
    }),
    (['--list'], {  # list alone, no host, no config file
        "config-file": "netbox.yml",
        "list": True,
        "host": None,
    }),
    ([], {  # list alone, no host, no config file
        "config-file": "netbox.yml",
        "list": False,
        "host": None,
    }),
])
def test_parse_cli_args_ok(args, exp):
    cli_args = parse_cli_args(args)

    assert cli_args.config_file.split("/")[-1] == exp['config-file']
    assert cli_args.list == exp['list']
    assert cli_args.host == exp['host']


@pytest.mark.parametrize("args", [
    (['-c', '--list']),  # missing config file name
])
def test_parse_cli_args_ko(args):
    with pytest.raises(SystemExit) as err:
        parse_cli_args(args)


@pytest.mark.parametrize("arg", [
    ({  # with only url
        "netbox": {
            "api": {
                "url": "http://test.com"
            }
        }
    }),
    ({  # with url and private key
        "netbox": {
            "api": {
                "url": "http://test.com",
                "private_key": "private key"
            }
        }
    }),
    ({  # with url and private key file
        "netbox": {
            "api": {
                "url": "http://test.com",
                "private_key_file": "private key"
            }
        }
    }),
    ({  # with url and ssl verify
        "netbox": {
            "api": {
                "url": "http://test.com",
                "ssl_verify": True
            }
        }
    }),
    ({  # with url and token
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "Test_token"
            }
        }
    }),
    ({  # with url and all arguments except private_key
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "Test_token",
                "ssl_verify": True,
                "private_key_file": "private key",
            }
        }
    }),
    ({  # with url and all arguments except private_key_file
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "Test_token",
                "ssl_verify": True,
                "private_key": "private key"
            }
        }
    }),
])
def test_validate_api_ok(arg):
    """Validate API configuration"""
    assert validate_configuration(arg) is None


@pytest.mark.parametrize("arg", [
    ({  # empty api section
        "nebtox": {
            "api": {}
        }
    }),
    ({  # missing URL
        "nebtox": {
            "api": {
                "token": "test"
            }
        }
    }),
    ({  # Both private_key and private_key_file
        "nebtox": {
            "api": {
                "url": "http://test.com",
                "private_key": "private key",
                "private_key_file": "private key"
            }
        }
    }),
    ({  # Additional property
        "nebtox": {
            "api": {
                "url": "http://test.com",
                "extra": "value"
            }
        }
    }),
])
def test_validate_api_ko(arg):
    """Validate API configuration structure errors"""
    with pytest.raises(SystemExit) as err:
        validate_configuration(arg)
    assert 4 == err.value.code


@pytest.mark.parametrize("arg", [
        ({  # containing devices with filters
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "filters": [  # Several filters
                                {"role_id": 3},
                                {"site_id": 4}
                            ],
                        },
                    }
                }
            }
        }),
        ({  # containing devices with group_by
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "group_by": [
                                ".device_role",
                                ".tags"
                            ],
                        },
                    }
                }
            }
        }),
        ({  # containing devices with group prefix
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "group_prefix": "dev_"
                        }
                    }
                }
            }
        }),
        ({  # containing devices with host_vars
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {"ip": "ip"}
                            ]
                        },
                    }
                }
            }
        }),
        ({  # containing devices with sub-imports
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "sub_import": [
                                {
                                    "stack": "a.b",
                                    "vars": [
                                        {
                                            "a": {
                                                "application": "whatever",
                                                "type": "whatever",
                                                "index": "whatever",
                                                "filter": {
                                                    "device_id": ".id",
                                                }
                                            }
                                        },
                                        {
                                            "b": {
                                                "application": "whatever",
                                                "type": "whatever",
                                                "index": "whatever",
                                                "filter": {
                                                    "device_id": ".id",
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                    }
                }
            }
        }),
        ({  # containing devices with all
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "filters": [
                                {"role_id": 3}
                            ],
                            "group_by": [
                                "device_role"
                            ],
                            "group_prefix": "dev_",
                            "host_vars": [
                                {"ip": "ip"}
                            ],
                            "sub_import": [
                                {
                                    "stack": "a.b",
                                    "vars": [
                                        {
                                            "a": {
                                                "application": "whatever",
                                                "type": "whatever",
                                                "index": "whatever",
                                                "filter": {
                                                    "device_id": ".id",
                                                }
                                            }
                                        },
                                        {
                                            "b": {
                                                "application": "whatever",
                                                "type": "whatever",
                                                "index": "whatever",
                                                "filter": {
                                                    "device_id": ".id",
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                    }
                }
            }
        }),
        ({  # containing devices with host_vars and racks with group_by
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {"ip": "ip"}
                            ]
                        },
                        "racks": {
                            "group_by": [
                                "device_role"
                            ],
                        },
                    }
                }
            }
        }),
        ({  # containing devices with filters
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "filters": [
                                {"role_id": 3}
                            ],
                        },
                    }
                }
            }
        }),
        ({  # containing devices with group_by
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "group_by": [
                                "device_role",
                                "tags"
                            ],
                        },
                    }
                }
            }
        }),
        ({  # containing devices with devices
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "group_prefix": "dev_",
                        },
                    }
                }
            }
        }),
        ({  # containing devices with host_vars
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {"ip": "ip"}
                            ]
                        },
                    }
                }
            }
        }),
        ({  # containing devices with all
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "filters": [
                                {"role_id": 3}
                            ],
                            "group_by": [
                                "device_role"
                            ],
                            "group_prefix": "dev_",
                            "host_vars": [
                                {"ip": "ip"}
                            ],
                        },
                    }
                }
            }
        }),
        ({  # containing devices with host_vars and racks with group_by
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {"ip": "ip"}
                            ]
                        },
                        "racks": {
                            "group_by": [
                                "device_role"
                            ],
                        },
                    }
                }
            }
        }),
        ({  # containing dcim with devices and virtualization with racks
            "netbox": {
                "api": {
                    "url": "http://test.com"
                },
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {"ip": "ip"}
                            ]
                        },
                    },
                    "virtualization": {
                        "racks": {
                            "group_by": [
                                "device_role"
                            ],
                        },
                    }
                }
            }
        }),
    ])
def test_validate_import_ok(api_config, arg):
    # full api section with import section
    arg["netbox"]["api"] = api_config
    assert validate_configuration(arg) is None


@pytest.mark.parametrize("arg", [
    (
        {  # empty import
            "netbox": {
                "import": {}
            }
        }
    ),
    (
        {  # forgot app
            "netbox": {
                "import": {
                    "devices": {
                        "group_prefix": "prefix"
                    }
                }
            }
        }
    ),
    (
        {  # empty app
            "netbox": {
                "import": {
                    "dcim": {}
                }
            }
        }
    ),
    (
        {  # empty type
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {}
                    }
                }
            }
        }
    ),
    (
        {  # Extra vars
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "extra": "vars"
                        }
                    }
                }
            }
        }
    ),
    (
        {  # bad prefix type
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "group_prefix": 1
                        }
                    }
                }
            }
        }
    ),
    (
        {  # bad filters type
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "filters": {
                                "role_id"
                            }
                        }
                    }
                }
            }
        }
    ),
    (
        {  # bad group_by type
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "group_by": {
                                "role_id": 2
                            }
                        }
                    }
                }
            }
        }
    ),
    (
        {  # empty group by
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "group_by": []
                        }
                    }
                }
            }
        }
    ),
    (
        {  # empty hostvars
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": []
                        }
                    }
                }
            }
        }
    ),
    (
        {  # bad host_vars type
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": {
                                "role_id": 2
                            }
                        }
                    }
                }
            }
        }
    ),
    (
        {  # bad host_vars extra key
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {
                                    "role_id": ".role.id",
                                    "extra key": "extra value",
                                }
                            ]
                        }
                    }
                }
            }
        }
    ),
    (
        {  # bad host_vars extra key
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {
                                    "role_id": ".role.id",
                                },
                                {
                                    "role_id": ".role.id",
                                    "other": "value"
                                }
                            ]
                        }
                    }
                }
            }
        }
    ),
    (
        {  # host_vars empty dict
            "netbox": {
                "import": {
                    "dcim": {
                        "devices": {
                            "host_vars": [
                                {},
                                {
                                    "role_id": ".role.id"
                                }
                            ]
                        }
                    }
                }
            }
        }
    ),
])
def test_validate_import_ko(api_config, arg):
    # full api section with import section
    arg["netbox"]["api"] = api_config
    with pytest.raises(SystemExit) as err:
        validate_configuration(arg)
    assert 4 == err.value.code


@pytest.mark.parametrize("arg", [
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "url": "http://test.com"
            },
            "render": [
                {
                    "module": "test",
                    "name": "test"
                },
            ]
        }
    }),
    ({  # Two renders
        "netbox": {
            "render": [
                {
                    "module": "test1",
                    "name": "test1"
                },
                {
                    "module": "2",
                    "name": "2"
                },
            ]
        }
    }),
    ({  # One renders
        "netbox": {
            "render": [
                {
                    "module": "test1",
                    "name": "test1"
                }
            ]
        }
    }),
])
def test_validate_render_ok(api_config, import_config, arg):
    arg["netbox"]["api"] = api_config
    arg["netbox"]["import"] = import_config
    assert validate_configuration(arg) is None


@pytest.mark.parametrize("arg", [
    (
        {
            "netbox": {
                "render": []
            }
        }
    ),
    (
        {
            "netbox": {
                "render": [
                    {
                        "module": "test",
                        "name": "test",
                        "extra": "value"
                    }
                ]
            }
        }
    ),
])
def test_validate_render_ko(api_config, import_config, arg):
    # full api section with import section
    arg["netbox"]["api"] = api_config
    arg["netbox"]["import"] = import_config
    with pytest.raises(SystemExit) as err:
        validate_configuration(arg)
    assert 4 == err.value.code


@pytest.mark.parametrize("arg", [
    ({
        # empty configuration
        # hence missing required 'netbox' key
    }),
    ({
        "netbox": {
            "api": {}  # missing required keys
        }
    }),
    ({
        "var1": {
            "api": {
                "url": "var1",
                "extra": True  # extra key
            }
        }
    }),
    ({
        "netbox": {
            "api": {
                "url": "http://test.com",
                "extra": True  # extra key
            }
        }
    }),
    ({  # both private key and private key file
        "netbox": {
            "api": {
                "url": "http://test.com",
                "private_key": "private key",
                "private_key_file": "private key file"
            }
        }
    }),
    ({
        "netbox": {
            "api": {
                "url": 1,  # bad type
                "token": {}  # bad type
            }
        }
    }),
    ({
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": "string"  # bad type
        }
    }),
    ({
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {}  # empty import section
        }
    }),
    ({
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {
                "devices": {
                    "group_by": []  # empty group_by
                }
            }
        },
    }),
    ({
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {
                "dcim": {
                    "devices": {
                        "host_vars": {}  # empty host_vars
                    }
                }
            }
        },
    }),
    ({
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {
                "dcim": {}  # empty app name
            }
        }
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {
                "dcim": {
                    "devices": {
                        "filters": {
                            "example": "example value"
                        },
                        "group_by": [
                            "device_role",
                            "tags"
                        ],
                        "group_prefix": "dev_",
                        "host_vars": {
                            "ip": "ip"
                        }
                    },
                    "racks": {
                        "group_by": []  # empty group by
                    }
                }
            }
        }
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {
                "dcim": {
                    "devices": {
                        "filters": {
                            "example": "example value"
                        },
                        "group_by": [
                            "device_role",
                            "tags"
                        ],
                        "group_prefix": "dev_",
                        "host_vars": {
                            "ip": "ip"
                        }
                    },
                    "racks": {
                        "filters": 1  # bad type on patter arg
                    }
                }
            }
        }
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {
                "dcim": {
                    "devices": {
                        "filters": {
                            "example": "example value"
                        },
                        "group_by": [
                            "device_role",
                            "tags"
                        ],
                        "group_prefix": "dev_",
                        "host_vars": {
                            "ip": "ip"
                        }
                    },
                    "racks": {
                        "extra": "test"  # extra arg
                    }
                }
            }
        }
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "token_test"
            },
            "import": {
                "dcim": {}  # empty section
            }
        }
    }),
])
def test_validate_configuration_ko(arg):
    with pytest.raises(SystemExit) as err:
        validate_configuration(arg)
    assert 4 == err.value.code

