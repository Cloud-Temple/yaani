import pytest
from yaani.yaani import (
    SourceLoader,
    FileSource,
    YaaniError
)


def test_instantiate_source_unknown_src_type():
    with pytest.raises(YaaniError):
        SourceLoader.Utils.instantiate_source(
            "unkown", {}
        )


def test_load_sources_ok(src_ldr, mocker):
    mocker.patch(
        "yaani.yaani.SourceLoader.Utils.instantiate_source",
        return_value=True
    )
    src_ldr.configuration = {
        "srcA": {
            "type": "test",
            "args": "test"
        },
        "srcB": {
            "type": "test",
            "args": "test"
        },
    }
    for src_name, src_def in src_ldr.load_sources().items():
        assert src_def


def test_load_sources_ko(src_ldr, mocker):
    mocker.patch(
        "yaani.yaani.SourceLoader.Utils.instantiate_source",
        return_value=True
    )
    # Missing a key
    src_ldr.configuration = {
        "srcA": {
            "type": "test",
        },
        "srcB": {
            "type": "test",
            "args": "test"
        },
    }
    with pytest.raises(YaaniError):
        src_ldr.load_sources()


def test_load_sources_ko(src_ldr, mocker):
    mocker.patch(
        "yaani.yaani.SourceLoader.Utils.instantiate_source",
        return_value=True
    )
    # Empty source name
    src_ldr.configuration = {
        "": {
            "type": "test",
        },
        "srcB": {
            "type": "test",
            "args": "test"
        },
    }
    with pytest.raises(YaaniError):
        src_ldr.load_sources()
