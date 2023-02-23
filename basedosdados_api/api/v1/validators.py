import re

from pathlib import Path

import json
import os
from django.conf import settings
from django.core.exceptions import ValidationError

current_site = os.getenv("url")


def validate_area_key(value):
    """Validate area hierarchy."""
    regex = re.compile(r"^[a-z]+(\.[a-z]+)*$")
    if not regex.match(value):
        raise ValidationError(
            f"Area '{value}' is not valid. Area must be a dot-separated string of lowercase letters."
        )


def validate_is_valid_area_key(value):
    """Validate area key is in BD dict."""
    with open(settings.BASE_DIR / "schemas/repository/bd_spatial_coverage_tree.json") as f:
        area_key_dict = json.load(f)
        area_key_dict = area_key_dict.get("result")
    if value not in area_key_dict.keys():
        raise ValidationError(
            f"Area '{value}' is not valid. Area must valid. See {current_site}/schemas/bd_spatial_coverage_tree/ for valid areas."
        )
