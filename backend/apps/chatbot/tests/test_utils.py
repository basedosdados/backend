# -*- coding: utf-8 -*-
import json
from typing import Any

from backend.apps.chatbot.utils.stream import _truncate_json

STR_MAX_LEN = 300
STR_LONG_LEN = 400
STR_REMAINING = STR_LONG_LEN - STR_MAX_LEN

LIST_MAX_LEN = 10
LIST_LONG_LEN = 15
LIST_REMAINING = LIST_LONG_LEN - LIST_MAX_LEN


def format_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def test_truncate_json_long_string():
    data = {"long_string": "a" * STR_LONG_LEN}
    json_string = json.dumps(data)
    truncated = _truncate_json(json_string, max_str_len=STR_MAX_LEN)
    expected_str = "a" * STR_MAX_LEN + f"... ({STR_REMAINING} more characters)"
    expected_json = format_json({"long_string": expected_str})
    assert truncated == expected_json


def test_truncate_json_long_list():
    data = {"long_list": list(range(LIST_LONG_LEN))}
    json_string = json.dumps(data)
    truncated = _truncate_json(json_string, max_list_len=LIST_MAX_LEN)
    expected_list = list(range(LIST_MAX_LEN)) + [f"... ({LIST_REMAINING} more items)"]
    expected_json = format_json({"long_list": expected_list})
    assert truncated == expected_json


def test_truncate_json_nested():
    data = {
        "short_string": "a" * 100,
        "nested_list": [
            {"short_string": "b" * 100, "long_string": "c" * STR_LONG_LEN, "int": 1, "float": 1.0}
            for _ in range(LIST_LONG_LEN)
        ],
        "nested_dict": {"long_string": "d" * STR_LONG_LEN},
    }
    json_string = json.dumps(data)
    truncated = _truncate_json(json_string, max_list_len=LIST_MAX_LEN, max_str_len=STR_MAX_LEN)
    expected_data = {
        "short_string": "a" * 100,
        "nested_list": [
            {
                "short_string": "b" * 100,
                "long_string": "c" * STR_MAX_LEN + f"... ({STR_REMAINING} more characters)",
                "int": 1,
                "float": 1.0,
            }
            for _ in range(LIST_MAX_LEN)
        ]
        + [f"... ({LIST_REMAINING} more items)"],
        "nested_dict": {
            "long_string": "d" * STR_MAX_LEN + f"... ({STR_REMAINING} more characters)"
        },
    }
    expected_json = format_json(expected_data)
    assert truncated == expected_json


def test_truncate_json_not_needed():
    data = {
        "short_string": "hello",
        "short_list": [1, 2, 3],
    }
    json_string = json.dumps(data)
    expected_json = format_json(data)
    assert _truncate_json(json_string) == expected_json


def test_truncate_json_invalid():
    invalid_json_string = '{"key": "value"'
    assert _truncate_json(invalid_json_string) == invalid_json_string
