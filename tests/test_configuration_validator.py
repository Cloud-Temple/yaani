import pytest
from yaani.yaani import (
    Validator,
    SourceLoader,
    YaaniError,
    DataSetLoader
)


@pytest.mark.parametrize("config", [
    ({  # Correct type
        "srcA": {
            "type": SourceLoader.SOURCE_TYPE.NETBOX_API,
            "args": {
                "key": "value"
            }
        }
    }),
    ({  # Correct type
        "srcA": {
            "type": SourceLoader.SOURCE_TYPE.FILE,
            "args": {
                "key": "value"
            }
        }
    }),
    ({  # Correct type
        "srcA": {
            "type": SourceLoader.SOURCE_TYPE.SCRIPT,
            "args": {
                "key": "value"
            }
        }
    }),
    ({  # 2 sources
        "srcA": {
            "type": SourceLoader.SOURCE_TYPE.FILE,
            "args": {
                "key": "value"
            }
        },
        "srcB": {
            "type": SourceLoader.SOURCE_TYPE.SCRIPT,
            "args": {
                "key": "value"
            }
        },
    }),
])
def test_validate_source_configuration(config, mocker):
    mocker.patch(
        "yaani.yaani.Validator.DataSources.validate_source_args",
        return_value=True
    )
    Validator.DataSources.validate_configuration(config)


@pytest.mark.parametrize("config", [
    ({  # Incorrect type
        "srcA": {
            "type": "incorrect",
            "args": {
                "key": "value"
            }
        }
    }),
    ({  # Empty dict
    }),
    ({  # Empty args
        "srcA": {
            "type": SourceLoader.SOURCE_TYPE.NETBOX_API,
            "args": {
            }
        }
    }),
    ([  # Bad container type
    ]),
    ({  # Bad args type
        "srcA": {
            "type": SourceLoader.SOURCE_TYPE.FILE,
            "args": []
        }
    }),
    ({  # Missing args type
        "srcA": {
            "type": SourceLoader.SOURCE_TYPE.FILE,
        }
    }),
    ({  # Missing type
        "src-A": {
            "args": {
                "key": "value"
            }
        }
    }),
    ({  # Incorrect src name
        "src A": {
            "args": {
                "key": "value"
            }
        }
    }),
    ({  # Extra key
        "srcA": {
            "extra": "key",
            "type": SourceLoader.SOURCE_TYPE.SCRIPT,
            "args": {
                "key": "value"
            }
        }
    }),
])
def test_validate_source_configuration_ko(config, mocker):
    mocker.patch(
        "yaani.yaani.Validator.DataSources.validate_source_args",
        return_value=True
    )
    with pytest.raises(YaaniError):
        Validator.DataSources.validate_configuration(config)


def test_validate_source_args_bad_src_type():
    with pytest.raises(YaaniError):
        Validator.DataSources.validate_source_args("unknown", {})


@pytest.mark.parametrize("config", [
    ({  # Only required args
        "url": "test/url",
    }),
    ({  # Full args with private_key
        "url": "test/url",
        "token": "test/url",
        "private_key": "private_key test",
        "ssl_verify": True
    }),
    ({  # Full args with private_key_file
        "url": "test/url",
        "token": "test/url",
        "private_key_file": "private_key_file test",
        "ssl_verify": True
    }),
])
def test_validate_netbox_api_source_args(config):
    Validator.DataSources.validate_source_args(
        SourceLoader.SOURCE_TYPE.NETBOX_API,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Empty
    }),
    ({  # Missing url
        "token": "test/url",
    }),
    ({  # Both private key options
        "url": "test/url",
        "token": "test/url",
        "private_key": "private_key test",
        "private_key_file": "private_key_file test",
    }),
    ({  # Extra key
        "url": "test/url",
        "token": "test/url",
        "private_key": "private_key test",
        "private_key_file": "private_key_file test",
        "extra": True
    }),
    ([  # Bad container type
    ]),
    ({  # Bad types
        "url": 1,
        "token": "test/url",
        "private_key": "private_key test",
        "ssl_verify": True
    }),
    ({  # Bad types
        "url": "test/url",
        "token": 1,
        "private_key": "private_key test",
        "ssl_verify": True
    }),
    ({  # Bad types
        "url": "test/url",
        "token": "test/url",
        "private_key": 1,
        "ssl_verify": True
    }),
    ({  # Bad types
        "url": "test/url",
        "token": "test/url",
        "private_key_file": 1,
        "ssl_verify": True
    }),
    ({  # Bad types
        "url": "test/url",
        "token": "test/url",
        "private_key": "private_key test",
        "ssl_verify": 1
    }),
    ({  # Empty strings
        "url": "",
        "token": "test/url",
        "private_key": "private_key test",
        "ssl_verify": True
    }),
    ({  # Empty strings
        "url": "test/url",
        "token": "",
        "private_key": "private_key test",
        "ssl_verify": True
    }),
    ({  # Empty strings
        "url": "test/url",
        "token": "test/url",
        "private_key": "",
        "ssl_verify": True
    }),
    ({  # Empty strings
        "url": "test/url",
        "token": "test/url",
        "private_key_file": "",
        "ssl_verify": True
    }),
])
def test_validate_netbox_api_source_args_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSources.validate_source_args(
            SourceLoader.SOURCE_TYPE.NETBOX_API,
            config
        )


@pytest.mark.parametrize("config", [
    ({
        "path": "test/path",
        "content_type": "json"
    }),
    ({
        "path": "test/path",
        "content_type": "yaml"
    }),
])
def test_validate_file_source_args(config):
    Validator.DataSources.validate_source_args(
        SourceLoader.SOURCE_TYPE.FILE,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Missing key path
        "content_type": "yaml"
    }),
    ({  # Missing key content_type
        "path": "test/path",
    }),
    ({  # Bad content type
        "path": "test/path",
        "content_type": "other"
    }),
    ({  # Empty strings
        "path": "",
        "content_type": "yaml"
    }),
    ({  # Empty strings
        "path": "test/path",
        "content_type": ""
    }),
    ({  # Extra key
        "path": "test/path",
        "extra": 1,
        "content_type": "yaml"
    }),
    ({  # Empty dict
    }),
    ([  # Bad type
    ]),
])
def test_validate_file_source_args_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSources.validate_source_args(
            SourceLoader.SOURCE_TYPE.FILE,
            config
        )


@pytest.mark.parametrize("config", [
    ({
        "path": "test/path",
        "content_type": "json"
    }),
    ({
        "path": "test/path",
        "content_type": "yaml"
    }),
])
def test_validate_script_source_args(config):
    Validator.DataSources.validate_source_args(
        SourceLoader.SOURCE_TYPE.SCRIPT,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Missing key path
        "content_type": "yaml"
    }),
    ({  # Missing key content_type
        "path": "test/path",
    }),
    ({  # Bad content type
        "path": "test/path",
        "content_type": "other"
    }),
    ({  # Empty strings
        "path": "",
        "content_type": "yaml"
    }),
    ({  # Empty strings
        "path": "test/path",
        "content_type": ""
    }),
    ({  # Extra key
        "path": "test/path",
        "extra": 1,
        "content_type": "yaml"
    }),
    ({  # Empty dict
    }),
    ([  # Bad type
    ]),
])
def test_validate_script_source_args_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSources.validate_source_args(
            SourceLoader.SOURCE_TYPE.SCRIPT,
            config
        )


@pytest.mark.parametrize("config", [
    ([  # Basic config
        {
            "name": "setA",
            "from": DataSetLoader.STRATEGY.SOURCE,
            "args": {}
        }
    ]),
    ([  # Basic config
        {
            "name": "setA",
            "from": DataSetLoader.STRATEGY.FILTERING,
            "args": {}
        }
    ]),
    ([  # Basic config
        {
            "name": "setA",
            "from": DataSetLoader.STRATEGY.MERGE,
            "args": {}
        }
    ]),
    ([  # Basic config
        {
            "name": "setA",
            "from": DataSetLoader.STRATEGY.DECORATION,
            "args": {}
        }
    ]),
    ([  # Basic config with list as args
        {
            "name": "setA",
            "from": DataSetLoader.STRATEGY.SOURCE,
            "args": []
        }
    ]),
    ([  # Basic config with list as args
        {
            "name": "setA",
            "from": DataSetLoader.STRATEGY.MERGE,
            "args": []
        }
    ]),
    ([  # Basic config with list as args
        {
            "name": "setA",
            "from": DataSetLoader.STRATEGY.DECORATION,
            "args": []
        }
    ]),
])
def test_validate_data_sets_configuration(config):
    Validator.DataSets.validate_configuration(config)


@pytest.mark.parametrize("config", [
    ([  # Empty config
    ]),
    ([  # Empty data set
        {}
    ]),
    ([  # Missing 'from' key
        {
            "name": "SetA",
            "args": []
        }
    ]),
    ([  # Missing 'args' key
        {
            "name": "SetA",
            "from": DataSetLoader.STRATEGY.DECORATION,
        }
    ]),
    ([  # Wrong 'from' key
        {
            "from": "Wrong",
            "args": []
        }
    ]),
    ([  # Extra key
        {
            "from": DataSetLoader.STRATEGY.DECORATION,
            "extra": "key",
            "args": []
        }
    ]),
    ([  # Missing key 'name'
        {
            "from": DataSetLoader.STRATEGY.DECORATION,
            "args": []
        }
    ]),
    ([  # Empty key 'name'
        {
            "name": "",
            "from": DataSetLoader.STRATEGY.DECORATION,
            "args": []
        }
    ]),
])
def test_validate_data_sets_configuration_ko(config, mocker):
    mocker.patch(
        "yaani.yaani.Validator.DataSources.validate_source_args",
        return_value=True
    )
    with pytest.raises(YaaniError):
        Validator.DataSources.validate_configuration(config)


@pytest.mark.parametrize("config", [
    ({  # Basic config
        "name": "SrcA",
        "filter": ".[]"
    }),
])
def test_validate_data_sets_args_file_source(config):
    Validator.DataSets.validate_data_set_args(
        DataSetLoader.STRATEGY.FILE_SOURCE,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Missing 'name'
        "filter": ".[]"
    }),
    ({  # Missing 'filter'
        "name": "SrcA",
    }),
    ({  # Empty
    }),
    ({  # Extra key
        "name": "SrcA",
        "extra": "whatever",
        "filter": ".[]"
    }),
    ({  # Empty 'name'
        "name": "",
        "filter": ".[]"
    }),
    ({  # Empty 'filter'
        "name": "SrcA",
        "filter": ""
    }),
])
def test_validate_data_sets_args_file_source_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSets.validate_data_set_args(
            DataSetLoader.STRATEGY.FILE_SOURCE,
            config
        )


@pytest.mark.parametrize("config", [
    ({  # Basic config
        "name": "setA",
        "filter": ".[]"
    }),
])
def test_validate_data_sets_args_filtering(config):
    Validator.DataSets.validate_data_set_args(
        DataSetLoader.STRATEGY.FILTERING,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Missing 'name'
        "filter": ".[]"
    }),
    ({  # Missing 'filter'
        "name": "setA",
    }),
    ({  # Empty
    }),
    ({  # Extra key
        "name": "setA",
        "extra": "whatever",
        "filter": ".[]"
    }),
    ({  # Empty 'name'
        "name": "",
        "filter": ".[]"
    }),
    ({  # Empty 'filter'
        "name": "setA",
        "filter": ""
    }),
])
def test_validate_data_sets_args_filtering_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSets.validate_data_set_args(
            DataSetLoader.STRATEGY.FILTERING,
            config
        )


@pytest.mark.parametrize("config", [
    ({  # Basic config
        "name": "SrcA",
        "app": "dcim",
        "type": "devices",
    }),
    ({  # Basic config - optional filters
        "name": "SrcA",
        "app": "dcim",
        "type": "devices",
        "filters": [
            {
                "tag": "router"
            },
        ],
    }),
])
def test_validate_data_sets_args_netbox_source(config):
    Validator.DataSets.validate_data_set_args(
        DataSetLoader.STRATEGY.NETBOX_SOURCE,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Empty
    }),
    ({  # Extra key
        "name": "SrcA",
        "Extra": "Extra",
        "app": "dcim",
        "type": "devices",
    }),
    ({  # Missing 'name'
        "app": "dcim",
        "type": "devices",
    }),
    ({  # Missing 'app'
        "name": "SrcA",
        "type": "devices",
    }),
    ({  # Missing 'type'
        "name": "SrcA",
        "app": "dcim",
    }),
    ({  # Empty 'name'
        "name": "",
        "app": "dcim",
        "type": "devices",
    }),
    ({  # Empty 'app'
        "name": "SrcA",
        "app": "",
        "type": "devices",
    }),
    ({  # Empty 'type'
        "name": "SrcA",
        "app": "dcim",
        "type": "",
    }),
    ({  # Bad filter type
        "name": "SrcA",
        "app": "dcim",
        "type": "devices",
        "filters": {}
    }),
    ({  # Empty filters
        "name": "SrcA",
        "app": "dcim",
        "type": "devices",
        "filters": {}
    }),
    ({  # Filters with empty dict
        "name": "SrcA",
        "app": "dcim",
        "type": "devices",
        "filters": [
            {},
        ],
    }),
])
def test_validate_data_sets_args_netbox_source_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSets.validate_data_set_args(
            DataSetLoader.STRATEGY.NETBOX_SOURCE,
            config
        )


@pytest.mark.parametrize("config", [
    ({  # Basic config
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
            {
                "name": "set2",
                "pivot": "query",
            },
        ],
    }),
    ({  # Basic config - more items in keys
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
            {
                "name": "set2",
                "pivot": "query",
            },
        ],
        "keys": {
            "key1": "set1",
            "key2": "set2",
        }
    }),
    ({  # More items in sets
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
            {
                "name": "set2",
                "pivot": "query",
            },
            {
                "name": "set3",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": "set1"
        }
    }),
])
def test_validate_data_sets_args_merge(config):
    Validator.DataSets.validate_data_set_args(
        DataSetLoader.STRATEGY.MERGE,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Missing key 'sets'
    }),
    ({  # Not enough items in sets
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Missing key 'name' in sets item
        "sets": [
            {
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
    }),
    ({  # Missing key 'pivot' in sets item
        "sets": [
            {
                "name": "set1",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
    }),
    ({  # Empty key 'name' in sets item
        "sets": [
            {
                "name": "",
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Empty key 'pivot' in sets item
        "sets": [
            {
                "name": "set1",
                "pivot": "",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Bad sets type
        "sets": {},
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Empty 'keys'
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {}
    }),
    ({  # Empty value for a key in keys
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": ""
        }
    }),
    ({  # Bad type for 'name' in sets item
        "sets": [
            {
                "name": 2,
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Bad type for 'pivot' in sets item
        "sets": [
            {
                "name": "set1",
                "pivot": 2,
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Bad 'keys' type
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": []
    }),
    ({  # Extra key at root
        "sets": [
            {
                "name": "set1",
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "extra": "extra",
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Extra key in sets item
        "sets": [
            {
                "name": "set1",
                "extra": "extra",
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": "set1"
        }
    }),
    ({  # Bad type for a value in keys
        "sets": [
            {
                "name": "set1",
                "extra": "extra",
                "pivot": "query",
            },
            {
                "name": "set1",
                "pivot": "query",
            },
        ],
        "keys": {
            "key": 1
        }
    }),
])
def test_validate_data_sets_args_merge_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSets.validate_data_set_args(
            DataSetLoader.STRATEGY.MERGE,
            config
        )


@pytest.mark.parametrize("config", [
    ({  # Basic config
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Basic config -- w/ exclusive
        "main": {
            "name": "set1",
            "pivot": "query",
            "exclusive": True,
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Basic config - more decorators
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set4",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
])
def test_validate_data_sets_args_decoration(config):
    Validator.DataSets.validate_data_set_args(
        DataSetLoader.STRATEGY.DECORATION,
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Empty config
    }),
    ({  # Missing key 'main'
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Missing key 'decorators'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
    }),
    ({  # Empty key 'main'
        "main": {},
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Empty key 'decorators'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [],
    }),
    ({  # Bad type for 'main'
        "main": [],
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Bad type for 'decorators'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": {}
    }),
    ({  # Missing 'name' in main
        "main": {
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Missing 'pivot' in main
        "main": {
            "name": "set1",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Empty 'name' in main
        "main": {
            "name": "",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Empty 'pivot' in main
        "main": {
            "name": "set1",
            "pivot": "",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Bad type for 'name' in main
        "main": {
            "name": 1,
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Bad type for 'exclusive' in main
        "main": {
            "name": "Set1",
            "pivot": "query",
            "exclusive": "false",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Bad type for 'pivot' in main
        "main": {
            "name": "set1",
            "pivot": 1,
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - missing 'name'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - missing 'pivot'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - missing 'anchor'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - Empty 'name'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - Empty 'pivot'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - Empty 'anchor'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": ""
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - Bad type for 'name'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": 1,
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - Bad type for 'pivot'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": 1,
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Decorator item - Bad type for 'anchor'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": 1
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Extra key in 'main'
        "main": {
            "extra": "extra",
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Extra key for item in 'decorators'
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "decorators": [
            {
                "name": "set2",
                "extra": "extra",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
    ({  # Extra key at root
        "main": {
            "name": "set1",
            "pivot": "query",
        },
        "extra": "extra",
        "decorators": [
            {
                "name": "set2",
                "pivot": "query",
                "anchor": "key_name"
            },
            {
                "name": "set3",
                "pivot": "query",
                "anchor": "key_name"
            },
        ],
    }),
])
def test_validate_data_sets_args_decoration_ko(config):
    with pytest.raises(YaaniError):
        Validator.DataSets.validate_data_set_args(
            DataSetLoader.STRATEGY.DECORATION,
            config
        )


@pytest.mark.parametrize("config", [
    ({  # Basic config
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                },
            }
        ]
    }),
    ({  # Basic config - with more keys
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                },
            }
        ],
        "group_vars": [
            {
                "group": "test",
                "set": "test",
            },
        ],
    }),
    ({  # Basic config - with more keys
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                },
            }
        ],
        "group_vars": [
            {
                "group": "test",
                "set": "test",
            },
            {
                "group": "test",
                "set": "test",
            },
        ],
        "group_hierarchy": {
            "root": {
                "leaf": None
            }
        }
    }),
    ({  # Basic config - deeper hierarchy
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                },
            }
        ],
        "group_vars": [
            {
                "group": "test",
                "set": "test",
            },
            {
                "group": "test",
                "set": "test",
            },
        ],
        "group_hierarchy": {
            "root": {
                "leaf": {
                    "sub_leaf": None
                }
            }
        }
    }),
    ({  # Basic config - full options
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "build",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "build",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "build",
                        },
                        {
                            "value": "whatever",
                            "namespace": "build",
                        },
                        {
                            "value": "whatever",
                            "namespace": "build",
                        },
                    ],
                },
            },
        ]
    }),
])
def test_validate_render_validate_configuration(config):
    Validator.Render.validate_configuration(
        config
    )


@pytest.mark.parametrize("config", [
    ({  # Root - Empty config
    }),
    ({  # Root - Bad type for 'elements'
        "elements": {},
    }),
    ({  # Root - Bad type for 'group_vars'
        "elements": [],
        "group_vars": {},
    }),
    ({  # Root - Bad type for 'group_hierarchy'
        "elements": {},
        "group_hierarchy": [],
    }),
    ({  # Root - extra key
        "extra": "extra",
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item lvl 1 - Missing key 'name'
        "elements": [
            {
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item lvl 1 - Extra key
        "elements": [
            {
                "name": "set1",
                "extra": "extra",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item lvl 1 - Missing key 'args'
        "elements": [
            {
                "name": "set1",
            },
        ]
    }),
    ({  # Sets item lvl 1 - Empty key 'name'
        "elements": [
            {
                "name": "",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item lvl 1 - Bad type for key 'name'
        "elements": [
            {
                "name": 1,
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad type for 'group_prefix'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": 1,
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Extra key
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "extra": "extra",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Empty 'pre_condition'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad type for 'pre_condition'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": 1,
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Empty 'host_vars'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {},
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad type for 'host_vars'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": [],
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad type for 'host_vars' value
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": 1,
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Empty 'host_vars' value
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad type for 'post_condition'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": [],
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Empty 'post_condition'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {},
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['post_condition'] - Empty 'value'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['post_condition'] - Empty 'namespace'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Extra key in 'post_condition'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "extra": "extra",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Missing 'value' in 'post_condition'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['index'] - Empty 'value'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['index'] - Empty 'namespace'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['index'] - Bad type for 'namespace'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": 1,
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['index'] - Bad type for 'value'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": 1,
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['index'] - Extra key
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "extra": "extra",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['index'] -  Empty
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {},
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'] - Bad type
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": {}
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'] - Empty
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'][] - Empty key 'value'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'][] - Empty key 'namespace'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'][] - Missing key 'value'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'][] - Bad type for 'value'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": 1,
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'][] - Bad type for 'namespace'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": 1,
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args']['group_by'][] - Extra key
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                            "extra": "extra",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad namespace
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "other",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad namespace
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "other",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # Sets item ['args'] - Bad namespace
        "elements": [
            {
                "name": "set1",
                "args": {
                    "group_prefix": "prefix",
                    "pre_condition": "query",
                    "host_vars": {
                        "host_var1": "query",
                        "host_var2": "query",
                        "host_var3": "query",
                    },
                    "post_condition": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    },
                    "group_by": [
                        {
                            "value": "whatever",
                            "namespace": "other",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                        {
                            "value": "whatever",
                            "namespace": "import",
                        },
                    ],
                },
            },
        ]
    }),
    ({  # group_vars - Bad type for group
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_vars": [
            {
                "group": 1,
                "set": "test",
            },
        ]
    }),
    ({  # group_vars - Empty key 'group'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_vars": [
            {
                "group": "",
                "set": "test",
            },
        ]
    }),
    ({  # group_vars - Bad type for set
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_vars": [
            {
                "group": "test",
                "set": 1,
            },
        ]
    }),
    ({  # group_vars - Empty key 'set'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_vars": [
            {
                "group": "test",
                "set": "",
            },
        ]
    }),
    ({  # group_vars - Empty
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_vars": []
    }),
    ({  # group_vars - Missing key 'group'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_vars": [
            {
                "set": "test",
            },
        ]
    }),
    ({  # group_vars - Missing key 'set'
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_vars": [
            {
                "group": "test",
            },
        ]
    }),
    ({  # group_hierarchy - Missing
        "elements": [
            {
                "name": "set1",
                "args": {
                    "index": {
                        "value": "whatever",
                        "namespace": "import",
                    }
                }
            }
        ],
        "group_hierarchy": {}
    })
])
def test_validate_render_validate_configuration_ko(config):
    with pytest.raises(YaaniError):
        Validator.Render.validate_configuration(
            config
        )


@pytest.mark.parametrize("config", [
    ([  # Basic config
        {
            "module": "custom_module",
            "func": "custom_func",
        }
    ]),
    ([  # Basic config - more elts
        {
            "module": "custom_module",
            "func": "custom_func",
        },
        {
            "module": "custom_module",
            "func": "custom_func",
        },
    ]),
    ([  # Empty config
    ]),
])
def test_validate_transform_validate_configuration(config):
    Validator.Transform.validate_configuration(
        config
    )


@pytest.mark.parametrize("config", [
    ([  # Missing key 'module'
        {
            "func": "custom_func",
        }
    ]),
    ([  # Missing key 'func'
        {
            "module": "custom_module",
        }
    ]),
    ([  # Empty key 'module'
        {
            "module": "",
            "func": "custom_func",
        }
    ]),
    ([  # Empty key 'func'
        {
            "module": "custom_module",
            "func": "",
        }
    ]),
    ([  # Bad type for 'module'
        {
            "module": 1,
            "func": "custom_func",
        }
    ]),
    ([  # Bad type for 'func'
        {
            "module": "custom_module",
            "func": 1,
        }
    ]),
    ([  # Extra key
        {
            "module": "custom_module",
            "extra": "extra",
            "func": "custom_func",
        }
    ]),

])
def test_validate_transform_validate_configuration_ko(config):
    with pytest.raises(YaaniError):
        Validator.Transform.validate_configuration(
            config
        )
