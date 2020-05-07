import pytest
from yaani.yaani import (
    SourceLoader,
    FileSource,
    YaaniError,
    TextSource,
    ScriptSource,
    NetboxSource,
)
from pynetbox.core.endpoint import Endpoint


def test_text_source_instation_good_args(mocker):
    mocker.patch.object(
        TextSource,
        "load",
        return_value=True
    )
    tsrc = TextSource({
        "path": "/what/ever/",
        "content_type": "yaml"
    })
    tsrc = TextSource({
        "path": "/what/ever/",
        "content_type": "json"
    })


def test_text_source_instation_bad_ctn_type():
    with pytest.raises(YaaniError):
        tsrc = TextSource({
            "path": "/what/ever/",
            "content_type": "bad_type"
        })


def test_text_source_filter(mocker):
    mocker.patch.object(
        TextSource,
        "load",
        return_value=True
    )
    tsrc = TextSource({
        "path": "/what/ever/",
        "content_type": "yaml"
    })
    ds = [
        {
            "name": "dev1",
            "id": 1
        },
        {
            "name": "dev2",
            "id": 2
        },
        {
            "name": "dev3",
            "id": 3
        },
        {
            "name": "dev4",
            "id": 4
        },
        {
            "name": "dev5",
            "id": 5
        }
    ]
    tsrc._dataset = ds

    assert tsrc.filter('.[]') == ds


def test_text_source_filter_bad_query(mocker):
    mocker.patch.object(
        TextSource,
        "load",
        return_value=True
    )
    tsrc = TextSource({
        "path": "/what/ever/",
        "content_type": "yaml"
    })
    ds = [
        {
            "name": "dev1",
            "id": 1
        },
        {
            "name": "dev2",
            "id": 2
        },
        {
            "name": "dev3",
            "id": 3
        },
        {
            "name": "dev4",
            "id": 4
        },
        {
            "name": "dev5",
            "id": 5
        }
    ]
    tsrc._dataset = ds
    with pytest.raises(YaaniError):
        tsrc.filter('.[') == ds


def test_script_source_instation_good_args(mocker):
    mocker.patch.object(
        ScriptSource,
        "load",
        return_value=True
    )
    tsrc = ScriptSource({
        "path": "/what/ever/",
        "content_type": "yaml"
    })
    tsrc = ScriptSource({
        "path": "/what/ever/",
        "content_type": "json"
    })


def test_script_source_instation_bad_ctn_type():
    with pytest.raises(YaaniError):
        tsrc = ScriptSource({
            "path": "/what/ever/",
            "content_type": "bad_type"
        })


def test_netbox_source_extract(mocker):
    all_value = [
        {
            "name": "dev1",
            "id": 1
        },
        {
            "name": "dev2",
            "id": 2
        },
    ]
    mocker.patch.object(
        Endpoint,
        'all',
        return_value=all_value
    )
    nb = NetboxSource({"url": "whatever"})
    assert nb.extract({
        "app": "dcim",
        "type": "devices",
    }) == all_value
