# -*- coding: utf-8 -*-
import json
from typing import Any

from backend.apps.chatbot.utils.stream import _truncate_json


def format_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def test_truncate_json_long_string():
    data = {"long_string": "a" * 600}
    json_string = json.dumps(data)
    truncated = _truncate_json(json_string)
    expected_str = "a" * 500 + "... (100 more characters)"
    expected_json = format_json({"long_string": expected_str})
    assert truncated == expected_json


def test_truncate_json_long_list():
    data = {"long_list": list(range(15))}
    json_string = json.dumps(data)
    truncated = _truncate_json(json_string)
    expected_list = list(range(10)) + ["... (5 more items)"]
    expected_json = format_json({"long_list": expected_list})
    assert truncated == expected_json


def test_truncate_json_nested():
    data = {
        "short_string": "a" * 100,
        "nested_list": [
            {"short_string": "b" * 10, "long_string": "c" * 600, "int": 1, "float": 1.0}
            for _ in range(15)
        ],
        "nested_dict": {"long_string": "d" * 600},
    }
    json_string = json.dumps(data)
    truncated = _truncate_json(json_string)
    expected_data = {
        "short_string": "a" * 100,
        "nested_list": [
            {
                "short_string": "b" * 10,
                "long_string": "c" * 500 + "... (100 more characters)",
                "int": 1,
                "float": 1.0,
            }
            for _ in range(10)
        ]
        + ["... (5 more items)"],
        "nested_dict": {"long_string": "d" * 500 + "... (100 more characters)"},
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
