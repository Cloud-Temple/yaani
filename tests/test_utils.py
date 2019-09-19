import pytest

from yaani import safe_url, parse_cli_args, validate_configuration


@pytest.mark.parametrize("arg,exp", [
    ("test/", "test/"),  # already correct url
    ("test", "test/"),  # missing slash
    ("test//", "test//"),  # double slash
    ("/", "/"),  # one char
    ("", "/"),  # empty string
])
def test_safe_url(arg, exp):
    assert safe_url(arg) == exp


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

    assert cli_args.config_file == exp['config-file']
    assert cli_args.list == exp['list']
    assert cli_args.host == exp['host']


@pytest.mark.parametrize("args", [
    (['-c', '--list']),  # missing config file name
])
def test_parse_cli_args_ko(args):
    with pytest.raises(SystemExit) as err:
        parse_cli_args(args)


@pytest.mark.parametrize("arg", [
    ({  # only api section with only url
        "netbox": {
            "api": {
                "api_url": "http://test.com"
            }
        }
    }),
    ({  # only api section with url and token
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "Test_token"
            }
        }
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": {
                "devices": {
                    "filter": "test_filter",
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
                    "filter": "test"
                }
            }
        }
    }),
])
def test_validate_configuration_ok(arg):
    assert validate_configuration(arg) is None


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
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "extra": True  # extra key
            }
        }
    }),
    ({
        "netbox": {
            "api": {
                "api_url": 1,  # bad type
                "api_token": {}  # bad type
            }
        }
    }),
    ({
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": "string"  # bad type
        }
    }),
    ({
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": {}  # empty import section
        }
    }),
    ({
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
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
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": {
                "devices": {
                    "host_vars": {}  # empty host_vars
                }
            }
        },
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": {
                "devices": {
                    "filter": "test_filter",
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
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": {
                "devices": {
                    "filter": "test_filter",
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
                    "filter": 1  # bad type on patter arg
                }
            }
        }
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": {
                "devices": {
                    "filter": "test_filter",
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
    }),
    ({  # full api section and import section containing devices with all
        # options
        "netbox": {
            "api": {
                "api_url": "http://test.com",
                "api_token": "token_test"
            },
            "import": {
                "devices": {}  # empty section
            }
        }
    }),
])
def test_validate_configuration_ko(arg):
    with pytest.raises(Exception) as err:
        validate_configuration(arg)
