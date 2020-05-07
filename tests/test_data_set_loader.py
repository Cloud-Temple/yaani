import pytest
from yaani.yaani import (
    SourceLoader,
    DataSource,
    TextSource,
    DataSetLoader,
    YaaniError
)


@pytest.mark.parametrize("elts,expected", [
    (
        [
            {
                "a": "1"
            },
            {
                "b": "1"
            },
        ],
        {
            "a": "1",
            "b": "1",
        }
    ),
    (
        [
            {
                "a": "1",
                "c": "2"
            },
            {
                "b": "1"
            },
        ],
        {
            "a": "1",
            "b": "1",
            "c": "2",
        }
    ),
    (
        [
            {},
            {},
        ],
        {}
    ),
    (
        [
            {},
            {
                "b": "1"
            },
        ],
        {
            "b": "1",
        }
    ),
    (
        [
            {
                "a": "1",
                "b": "2"
            },
            {
                "b": "1"
            },
        ],
        {
            "a": "1",
            "b": "2",
        }
    ),
    (
        [
            {
                "a": "1",
                "b": "1"
            },
            {
                "b": "2"
            },
        ],
        {
            "a": "1",
            "b": "1",
        }
    ),
    (
        [
            {
                "a": "1",
                "b": "1"
            },
            {
                "b": "2"
            },
            {
                "b": "3"
            },
        ],
        {
            "a": "1",
            "b": "1",
        }
    ),
    (
        [
            {
                "b": "3"
            },
            {
                "a": "2",
                "b": "2"
            },
            {
                "a": "1",
                "b": "1"
            },
        ],
        {
            "a": "2",
            "b": "3",
        }
    ),
    (
        [
            {
                "b": "3"
            },
            {
                "a": "2",
                "b": "2",
                "d": "4",
            },
            {
                "a": "1",
                "b": "1"
            },
        ],
        {
            "d": "4",
            "a": "2",
            "b": "3",
        }
    ),
])
def test_merge_elts(elts, expected):
    assert DataSetLoader.Utils.merge_elts(elts) == expected


@pytest.mark.parametrize("elt,data,expected", [
    (
        {
            "a": 1
        },
        [
            ('b', 3),
            (
                'c',
                {
                    "i": "example"
                }
            ),
        ],
        {
            "a": 1,
            "b": 3,
            "c": {
                "i": "example"
            },
        }
    ),
    (
        {
            "a": 1
        },
        [
            ('b', 3),
            (
                'c',
                {
                    "i": "example"
                }
            ),
            ('d', [1, 2, 3])
        ],
        {
            "a": 1,
            "b": 3,
            "c": {
                "i": "example"
            },
            "d": [1, 2, 3],
        }
    ),
])
def test_decorate_element(elt, data, expected):
    assert DataSetLoader.Utils.decorate_element(elt, data) == expected


@pytest.mark.parametrize("strategy, expected", [
    (DataSetLoader.STRATEGY.SOURCE, "from_source"),
    (DataSetLoader.STRATEGY.MERGE, "from_merge"),
    (DataSetLoader.STRATEGY.DECORATION, "from_decoration"),
    (DataSetLoader.STRATEGY.FILTERING, "from_filtering"),
])
def test_create_set(strategy, expected, mocker):
    mocker.patch(
        'yaani.yaani.DataSetLoader.Utils.create_dataset_from_source',
        return_value='from_source'
    )
    mocker.patch(
        'yaani.yaani.DataSetLoader.Utils.create_dataset_from_merge',
        return_value='from_merge'
    )
    mocker.patch(
        'yaani.yaani.DataSetLoader.Utils.decorate_dataset',
        return_value='from_decoration'
    )
    mocker.patch(
        'yaani.yaani.DataSetLoader.Utils.create_dataset_from_filtering',
        return_value='from_filtering'
    )
    assert (
        DataSetLoader.Utils
        .create_set(strategy, {}, {}, [])
    ) == expected


def test_create_set_wrong_strategy():
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.create_set(
            "unknown",
            {},
            {},
            []
        )


@pytest.mark.parametrize("query, elt_lst, overlap", [
    (".", [], False),  # Bad query
    (".a", [{"a": [1]}], False),  # List as index
    (".a", [{"a": [2]}], True),  # List as index
    (".a", [{"a": {"b": 1}}], False),  # Dict as index
    (".a", [{"a": {"b": 2}}], True),  # Dict as index
    (".a", [{"a": 2}, {"a": 2}], False),  # Non unique index
])
def test_map_elt_to_value_ko(query, elt_lst, overlap):
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.map_elt_to_value(query, elt_lst, overlap)


@pytest.mark.parametrize("query, elt_lst, overlap, expected", [
    (  # Basic config
        ".a",
        [
            {
                "a": 1
            },
            {
                "a": 2
            },
        ],
        False,
        {
            1: {
                "a": 1
            },
            2: {
                "a": 2
            },
        }
    ),
    (  # Null index
        ".a",
        [
            {
                "a": 1
            },
            {
                "a": 2
            },
            {
                "a": None,
                "att": "value"
            },
        ],
        False,
        {
            1: {
                "a": 1
            },
            2: {
                "a": 2
            },
        }
    ),
    (  # Only null index
        ".b",
        [
            {
                "a": 1
            },
            {
                "a": 2
            },
            {
                "a": None,
                "att": "value"
            },
        ],
        False,
        {}
    ),
    (  # Only one valid index
        ".att",
        [
            {
                "a": 1
            },
            {
                "a": 2
            },
            {
                "a": None,
                "att": "value"
            },
        ],
        False,
        {
            "value": {
                "a": None,
                "att": "value"
            },
        }
    ),
    (  # Overlap case
        ".a",
        [
            {
                "a": 1,
                "att": 1
            },
            {
                "a": 1,
                "att": 2
            },
            {
                "a": 2
            },
            {
                "a": None,
                "att": "value"
            },
        ],
        True,
        {
            1: [
                {
                    "a": 1,
                    "att": 1
                },
                {
                    "a": 1,
                    "att": 2
                },
            ],
            2: [
                {
                    "a": 2,
                },
            ],
        }
    ),
    (  # No elts
        ".a",
        [],
        False,
        {}
    ),
])
def test_map_elt_to_value(query, elt_lst, overlap, expected):
    assert (
        DataSetLoader.Utils
        .map_elt_to_value(query, elt_lst, overlap)
    ) == expected


@pytest.mark.parametrize("set_lst,arg,expected", [
    (  # Basic config w/o overlap
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "left": "left-1"},
                    {"id": 2, "left": "left-2"},
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "right": "right-1"},
                    {"id": 2, "right": "right-2"},
                ]
            ),
        ],
        {},
        [
            {"id": 1, "left": "left-1", "right": "right-1"},
            {"id": 2, "left": "left-2", "right": "right-2"},
        ]
    ),
    (  # Basic config w/o overlap - More elements in set-left
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "left": "left-1"},
                    {"id": 2, "left": "left-2"},
                    {"id": 3, "left": "left-3"},
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "right": "right-1"},
                    {"id": 2, "right": "right-2"},
                    {"id": 4, "right": "right-4"},
                ]
            ),
        ],
        {},
        [
            {"id": 1, "left": "left-1", "right": "right-1"},
            {"id": 2, "left": "left-2", "right": "right-2"},
            {"id": 3, "left": "left-3"},
            {"id": 4, "right": "right-4"},
        ]
    ),
    (  # Basic config w/o overlap - Null element
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "left": "left-1"},
                    {"id": 2, "left": "left-2"},
                    {}
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "right": "right-1"},
                    {"id": 2, "right": "right-2"},
                ]
            ),
        ],
        {},
        [
            {"id": 1, "left": "left-1", "right": "right-1"},
            {"id": 2, "left": "left-2", "right": "right-2"},
        ]
    ),
    (  # Basic config w/o overlap - Empty set
        [
            (
                "set-left", ".id",
                []
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "right": "right-1"},
                    {"id": 2, "right": "right-2"},
                ]
            ),
        ],
        {},
        [
            {"id": 1, "right": "right-1"},
            {"id": 2, "right": "right-2"},
        ]
    ),
    (  # Basic config w/o overlap - Both null sets
        [
            (
                "set-left", ".id",
                []
            ),
            (
                "set-right", ".id",
                []
            ),
        ],
        {},
        []
    ),
    (  # Basic config w/ overlap
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "x": "set1", "left": "left-1"},
                    {"id": 2, "x": "set1", "left": "left-2"},
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "x": "set2", "right": "right-1"},
                    {"id": 2, "x": "set2", "right": "right-2"},
                ]
            ),
        ],
        {},
        [
            {"id": 1, "x": "set1", "left": "left-1", "right": "right-1"},
            {"id": 2, "x": "set1", "left": "left-2", "right": "right-2"},
        ]
    ),
    (  # Basic config w/ overlap
        [
            (
                "set-right", ".id",
                [
                    {"id": 1, "x": "set2", "right": "right-1"},
                    {"id": 2, "x": "set2", "right": "right-2"},
                ]
            ),
            (
                "set-left", ".id",
                [
                    {"id": 1, "x": "set1", "left": "left-1"},
                    {"id": 2, "x": "set1", "left": "left-2"},
                ]
            ),
        ],
        {},
        [
            {"id": 1, "x": "set2", "left": "left-1", "right": "right-1"},
            {"id": 2, "x": "set2", "left": "left-2", "right": "right-2"},
        ]
    ),
    (  # Basic config w/ overlap - key priority
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "y": "set1", "left": "left-1"},
                    {"id": 2, "y": "set1", "left": "left-2"},
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "y": "set2", "right": "right-1"},
                    {"id": 2, "y": "set2", "right": "right-2"},
                ]
            ),
        ],
        {
            "y": "set-right"
        },
        [
            {"id": 1, "y": "set2", "left": "left-1", "right": "right-1"},
            {"id": 2, "y": "set2", "left": "left-2", "right": "right-2"},
        ]
    ),
    (  # Basic config w/o overlap - More sets, inexistant key in priorities
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "left": "left-1"},
                    {"id": 2, "left": "left-2"},
                ]
            ),
            (
                "set-center", ".id",
                [
                    {"id": 1, "center": "center-1"},
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "right": "right-1"},
                    {"id": 2, "right": "right-2"},
                ]
            ),
        ],
        {
            "y": "set-right"
        },
        [
            {
                "id": 1,
                "left": "left-1",
                "center": "center-1",
                "right": "right-1"
            },
            {"id": 2, "left": "left-2", "right": "right-2"},
        ]
    ),
    (  # Basic config w/ overlap - More sets, existant keys in priorities
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "x": "lft", "y": "lft", "z": "lft"},
                    {"id": 2, "x": "lft", "y": "lft", "z": "lft"},
                ]
            ),
            (
                "set-center", ".id",
                [
                    {"id": 1, "x": "cntr", "y": "cntr", "z": "cntr"},
                    {"id": 2, "x": "cntr", "y": "cntr", "z": "cntr"},
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "x": "rght", "y": "rght", "z": "rght"},
                    {"id": 2, "x": "rght", "y": "rght", "z": "rght"},
                ]
            ),
        ],
        {
            "x": "set-center",
            "y": "set-right",
        },
        [
            {"id": 1, "x": "cntr", "y": "rght", "z": "lft"},
            {"id": 2, "x": "cntr", "y": "rght", "z": "lft"},
        ]
    ),
    (  # Basic config w/ overlap - no priorities, 3 sets
        [
            (
                "set-left", ".id",
                [
                    {"id": 1, "x": "lft", "y": "lft", "z": "lft"},
                    {"id": 2, "x": "lft", "y": "lft", "z": "lft"},
                ]
            ),
            (
                "set-center", ".id",
                [
                    {"id": 1, "x": "cntr", "y": "cntr", "z": "cntr"},
                    {"id": 2, "x": "cntr", "y": "cntr", "z": "cntr"},
                ]
            ),
            (
                "set-right", ".id",
                [
                    {"id": 1, "x": "rght", "y": "rght", "z": "rght"},
                    {"id": 2, "x": "rght", "y": "rght", "z": "rght"},
                ]
            ),
        ],
        {},
        [
            {"id": 1, "x": "lft", "y": "lft", "z": "lft"},
            {"id": 2, "x": "lft", "y": "lft", "z": "lft"},
        ]
    ),
])
def test_merge_sets(set_lst, arg, expected, mocker):
    assert DataSetLoader.Utils.merge_sets(set_lst, arg) == expected


def test_create_dataset_from_source_ko():
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.create_dataset_from_source(
            {"name": "src1"},
            {}
        )


def test_create_dataset_from_filtering():
    assert DataSetLoader.Utils.create_dataset_from_filtering(
        {
            "name": "setA",
            "filter": "."
        },
        {"setA": [1, 2, 3]}
    ) == [1, 2, 3]


def test_create_dataset_from_filtering_unknown_set():
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.create_dataset_from_filtering(
            {
                "name": "setA",
                "filter": ".[]"
            },
            {}
        )


def test_create_dataset_from_filtering_bad_query():
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.create_dataset_from_filtering(
            {
                "name": "setA",
                "filter": ".["
            },
            {"setA": {}}
        )


def test_create_dataset_from_merge(mocker):
    mocker.patch(
        'yaani.yaani.DataSetLoader.Utils.merge_sets',
        return_value=True
    )
    args = {
        "sets": [
            {"name": "set1", "pivot": "."},
            {"name": "set2", "pivot": "."},
        ]
    }
    assert DataSetLoader.Utils.create_dataset_from_merge(
        args,
        {"set1": None, "set2": None}
    )


def test_create_dataset_from_merge_missing_set(mocker):
    mocker.patch(
        'yaani.yaani.DataSetLoader.Utils.merge_sets',
        return_value=True
    )
    args = {
        "sets": [
            {"name": "set1", "pivot": "."},
            {"name": "set2", "pivot": "."},
        ]
    }
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.create_dataset_from_merge(
            args,
            {"set2": None}
        )


def test_decorate_dataset_missing_set1():
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.decorate_dataset(
            config={
                "main": {
                    "name": "set1",
                    "pivot": ".id"
                },
                "decorators": [
                    {
                        "name": "set2",
                        "pivot": ".id"
                    },
                ]
            },
            data_sets={"set1": []}
        )


def test_decorate_dataset_missing_set2():
    with pytest.raises(YaaniError):
        DataSetLoader.Utils.decorate_dataset(
            config={
                "main": {
                    "name": "set1",
                    "pivot": ".id"
                },
                "decorators": [
                    {
                        "name": "set2",
                        "pivot": ".id"
                    },
                ]
            },
            data_sets={"set2": []}
        )
