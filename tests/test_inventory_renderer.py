import pytest
from yaani.yaani import (
    InventoryRenderer,
    YaaniError
)


@pytest.mark.parametrize("condition,elts,rndrd_ns,expected", [
    (  # Basic config on import namespace
        ".id <= 2",
        [
            ({"id": 1}, {}),
            ({"id": 2}, {}),
            ({"id": 3}, {}),
            ({"id": 4}, {}),
        ],
        False,
        [
            ({"id": 1}, {}),
            ({"id": 2}, {}),
        ]
    ),
    (  # Basic config on render namespace
        ".rndrd_id <= 2",
        [
            ({"id": 1}, {"rndrd_id": 1}),
            ({"id": 2}, {"rndrd_id": 2}),
            ({"id": 3}, {"rndrd_id": 3}),
            ({"id": 4}, {"rndrd_id": 4}),
        ],
        True,
        [
            ({"id": 1}, {"rndrd_id": 1}),
            ({"id": 2}, {"rndrd_id": 2}),
        ]
    ),
    (  # Inexistant key
        ".a <= 2",
        [
            ({"id": 1}, {"rndrd_id": 1}),
            ({"id": 2}, {"rndrd_id": 2}),
            ({"id": 3}, {"rndrd_id": 3}),
            ({"id": 4}, {"rndrd_id": 4}),
        ],
        True,
        [
            ({"id": 1}, {"rndrd_id": 1}),
            ({"id": 2}, {"rndrd_id": 2}),
            ({"id": 3}, {"rndrd_id": 3}),
            ({"id": 4}, {"rndrd_id": 4}),
        ]
    ),
    (  # Exclude all
        ".id == 0",
        [
            ({"id": 1}, {"rndrd_id": 1}),
            ({"id": 2}, {"rndrd_id": 2}),
            ({"id": 3}, {"rndrd_id": 3}),
            ({"id": 4}, {"rndrd_id": 4}),
        ],
        False,
        []
    ),
    (  # Empty elements
        ".id <= 2",
        [],
        False,
        []
    ),
])
def test_apply_condition(condition, elts, rndrd_ns, expected):
    assert InventoryRenderer.Utils.apply_condition(
        condition, elts, rndrd_ns=rndrd_ns
    ) == expected


@pytest.mark.parametrize("condition,elts,rndrd_ns", [
    (  # Bad query
        ".i[d <= 2",
        [
            ({"id": 1}, {}),
            ({"id": 2}, {}),
            ({"id": 3}, {}),
            ({"id": 4}, {}),
        ],
        False
    ),
])
def test_apply_condition_ko(condition, elts, rndrd_ns):
    with pytest.raises(YaaniError):
        InventoryRenderer.Utils.apply_condition(
            condition, elts, rndrd_ns=rndrd_ns
        )


@pytest.mark.parametrize("config,data_set,expected", [
    (  # Basic config
        {
            "a": ".a",
            "b": ".b",
        },
        [
            ({"a": "a-1", "b": "b-1", "c": "c-1"}, {}),
            ({"a": "a-2", "b": "b-2", "c": "c-2"}, {}),
        ],
        [
            (
                {"a": "a-1", "b": "b-1", "c": "c-1"},
                {"a": "a-1", "b": "b-1"}
            ),
            (
                {"a": "a-2", "b": "b-2", "c": "c-2"},
                {"a": "a-2", "b": "b-2"}
            ),
        ]
    ),
    (  # Basic config - no host var definitions
        {},
        [
            ({"a": "a-1", "b": "b-1", "c": "c-1"}, {}),
            ({"a": "a-2", "b": "b-2", "c": "c-2"}, {}),
        ],
        [
            (
                {"a": "a-1", "b": "b-1", "c": "c-1"},
                {"a": "a-1", "b": "b-1", "c": "c-1"}
            ),
            (
                {"a": "a-2", "b": "b-2", "c": "c-2"},
                {"a": "a-2", "b": "b-2", "c": "c-2"}
            ),
        ],
    ),
    (  # Basic config - inexistant key
        {
            "a": ".a",
            "b": ".d",
        },
        [
            ({"a": "a-1", "b": "b-1", "c": "c-1"}, {}),
            ({"a": "a-2", "b": "b-2", "c": "c-2"}, {}),
        ],
        [
            (
                {"a": "a-1", "b": "b-1", "c": "c-1"},
                {"a": "a-1", "b": None}
            ),
            (
                {"a": "a-2", "b": "b-2", "c": "c-2"},
                {"a": "a-2", "b": None}
            ),
        ]
    ),
    (  # Basic config - Empty set
        {
            "a": ".a",
            "b": ".d",
        },
        [],
        []
    ),
])
def test_render_host_vars(config, data_set, expected):
    assert InventoryRenderer.Utils.render_host_vars(
        config=config,
        data_set=data_set
    ) == expected


@pytest.mark.parametrize("config,data_set", [
    (  # Bad query
        {
            "a": ".a3w[",
            "b": ".b",
        },
        [
            ({"a": "a-1", "b": "b-1", "c": "c-1"}, {}),
            ({"a": "a-2", "b": "b-2", "c": "c-2"}, {}),
        ]
    ),
])
def test_render_host_vars_bad(config, data_set):
    with pytest.raises(YaaniError):
        assert InventoryRenderer.Utils.render_host_vars(
            config=config,
            data_set=data_set
        )


@pytest.mark.parametrize("config,data_set,expected", [
    (  # Basic Config
        {
            "value": ".a",
        },
        [
            ({"a": 1}, {}),
            ({"a": 2}, {}),
        ],
        {
            1: ({"a": 1}, {}),
            2: ({"a": 2}, {}),
        },
    ),
    (  # Basic Config
        {
            "value": ".a",
        },
        [],
        {},
    ),
    (  # Basic Config
        {
            "value": ".a",
        },
        [
            ({"a": 1}, {}),
            ({"b": 2}, {}),
        ],
        {
            1: ({"a": 1}, {}),
        },
    ),
    (  # Basic Config
        {
            "value": ".a",
            "namespace": "import",
        },
        [
            ({"a": 1}, {}),
            ({"a": 2}, {}),
        ],
        {
            1: ({"a": 1}, {}),
            2: ({"a": 2}, {}),
        },
    ),
    (  # Basic Config
        {
            "value": ".a",
            "namespace": "build",
        },
        [
            ({"a": 1}, {"a": 3}),
            ({"a": 2}, {"a": 4}),
        ],
        {
            3: ({"a": 1}, {"a": 3}),
            4: ({"a": 2}, {"a": 4}),
        },
    ),
])
def test_index_elements(config, data_set, expected):
    assert InventoryRenderer.Utils.index_elements(
        config,
        data_set
    ) == expected


def test_index_elements_bad_query():
    with pytest.raises(YaaniError):
        InventoryRenderer.Utils.index_elements(
            {"value": ".]", "namespace": "import"},
            []
        )


def test_index_elements_bad_args():
    with pytest.raises(YaaniError):
        InventoryRenderer.Utils.index_elements(
            {"namespace": "import"},
            []
        )


def test_index_elements_index_duplicates():
    with pytest.raises(YaaniError):
        InventoryRenderer.Utils.index_elements(
            {"value": ".a"},
            [
                ({"a": 1}, {"a": 3}),
                ({"a": 1}, {"a": 4}),
            ],
        )
    with pytest.raises(YaaniError):
        InventoryRenderer.Utils.index_elements(
            {"value": ".a", "namespace": "build"},
            [
                ({"a": 1}, {"a": 3}),
                ({"a": 1}, {"a": 3}),
            ],
        )


def test_index_elements_list_index():
    with pytest.raises(YaaniError):
        InventoryRenderer.Utils.index_elements(
            {"value": ".a"},
            [
                ({"a": [1]}, {"a": 3}),
                ({"a": [2]}, {"a": 3}),
            ],
        )


def test_index_elements_dict_index():
    with pytest.raises(YaaniError):
        InventoryRenderer.Utils.index_elements(
            {"value": ".a"},
            [
                ({"a": {"1": "1"}}, {"a": 3}),
                ({"a": {"2": "2"}}, {"a": 4}),
            ],
        )


@pytest.mark.parametrize("element_name,group_name,inventory,expected", [
    (  # Basic config - Empty inventory
        "elt1", "grp1",
        {},
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt1"
                ]
            }
        }
    ),
    (  # Basic config - Already existing empty group
        "elt1", "grp1",
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": []
            }
        },
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt1"
                ]
            }
        }
    ),
    (  # Basic config - already existing group with other elt
        "elt1", "grp1",
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt2"
                ]
            }
        },
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt2",
                    "elt1"
                ]
            }
        }
    ),
    (  # Basic config - other group
        "elt1", "grp1",
        {
            "grp2": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt2"
                ]
            }
        },
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt1"
                ]
            },
            "grp2": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt2"
                ]
            }
        }
    ),
    (  # Basic config - already in group
        "elt1", "grp1",
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt1"
                ]
            },
            "grp2": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt2"
                ]
            }
        },
        {
            "grp1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt1"
                ]
            },
            "grp2": {
                "vars": {},
                "children": [],
                "hosts": [
                    "elt2"
                ]
            }
        }
    ),
])
def test_add_element_to_group(element_name, group_name, inventory, expected):
    assert InventoryRenderer.Utils.add_element_to_group(
        element_name,
        group_name,
        inventory
    ) == expected


@pytest.mark.parametrize("indexed_data_set, group_by, inventory, expected", [
    (  # Empty group by
        {},
        [],
        {},
        {}
    ),
    (  # Basic use
        {
            "1": ({
                "site": 1
            }, {}),
            "2": ({
                "site": 2
            }, {}),
        },
        [
            {"value": ".site"}
        ],
        {},
        {
            "_1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1"
                ]
            },
            "_2": {
                "vars": {},
                "children": [],
                "hosts": [
                    "2"
                ]
            },
        }
    ),
    (  # Basic use
        {
            "1": ({
                "site": 1
            }, {}),
            "2": ({
                "site": 1
            }, {}),
        },
        [
            {"value": ".site"}
        ],
        {},
        {
            "_1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1", "2"
                ]
            },
        }
    ),
    (  # Basic use
        {
            "1": ({
                "site": 1
            }, {}),
            "2": ({
                "site": 1
            }, {}),
            "3": ({
            }, {}),
        },
        [
            {"value": ".site"}
        ],
        {},
        {
            "_1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1", "2"
                ]
            },
        }
    ),
    (  # Basic use - namespace 'build'
        {
            "1": ({}, {
                "site": 1
            }),
            "2": ({}, {
                "site": 1
            }),
            "3": ({}, {
            }),
        },
        [
            {
                "value": ".site",
                "namespace": "build",
            }
        ],
        {},
        {
            "_1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1", "2"
                ]
            },
        }
    ),
    (  # namespace 'build' - list value
        {
            "1": ({}, {
                "site": [1, 2]
            }),
            "2": ({}, {
                "site": 1
            }),
            "3": ({}, {
            }),
        },
        [
            {
                "value": ".site",
                "namespace": "build",
            },
        ],
        {},
        {
            "_1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1", "2"
                ]
            },
            "_2": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1"
                ]
            },
        }
    ),
    (  # namespace 'build' - double grouping - list value
        {
            "1": ({}, {
                "site": [1, 2]
            }),
            "2": ({}, {
                "site": 1
            }),
            "3": ({}, {
                "a": "grpA"
            }),
        },
        [
            {
                "value": ".site",
                "namespace": "build",
            },
            {
                "value": ".a",
                "namespace": "build",
            },
        ],
        {},
        {
            "_1": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1", "2"
                ]
            },
            "_2": {
                "vars": {},
                "children": [],
                "hosts": [
                    "1"
                ]
            },
            "_grpA": {
                "vars": {},
                "children": [],
                "hosts": [
                    "3"
                ]
            },
        }
    ),
])
def test_render_group_by(indexed_data_set, group_by, inventory, expected):
    assert InventoryRenderer.Utils.render_group_by(
        indexed_data_set,
        group_by,
        "_",
        inventory
    ) == expected


def test_render_group_by_bad_query():
    with pytest.raises(YaaniError):
        assert InventoryRenderer.Utils.render_group_by(
            {},
            [{"value": ".]"}],
            "_",
            {}
        )
