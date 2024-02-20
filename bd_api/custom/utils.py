# -*- coding: utf-8 -*-
import string


def check_snake_case(name: str) -> bool:
    allowed_chars = set(string.ascii_lowercase + string.digits + "_")
    return set(name).issubset(allowed_chars) and name[0] != "_"


def check_kebab_case(name: str) -> bool:
    allowed_chars = set(string.ascii_lowercase + string.digits + "-")
    return set(name).issubset(allowed_chars) and name[0] != "-"
