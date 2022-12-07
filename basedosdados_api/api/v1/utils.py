# -*- coding: utf-8 -*-
"""
General-purpose functions for the API.
"""

import string


def check_snake_case(name: str) -> bool:
    """
    Check if a string is in snake_case.
    """
    allowed_chars = set(string.ascii_lowercase + string.digits + "_")
    return set(name).issubset(allowed_chars) and name[0] != "_"
