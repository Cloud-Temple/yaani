import pytest

from yaani import parse_cli_args, validate_configuration


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
                "url": "http://test.com"
            }
        }
    }),
    ({  # only api section with url and private key
        "netbox": {
            "api": {
                "url": "http://test.com",
                "private_key": "private key"
            }
        }
    }),
    ({  # only api section with url and private key file
        "netbox": {
            "api": {
                "url": "http://test.com",
                "private_key_file": "private key"
            }
        }
    }),
    ({  # only api section with url and ssl verify
        "netbox": {
            "api": {
                "url": "http://test.com",
                "ssl_verify": True
            }
        }
    }),
    ({  # only api section with url and token
        "netbox": {
            "api": {
                "url": "http://test.com",
                "token": "Test_token"
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
                            "role_id": 3
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
                        "filters": {
                            "role_id": 4
                        }
                    }
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
    with pytest.raises(Exception) as err:
        validate_configuration(arg)
