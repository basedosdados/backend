# -*- coding: utf-8 -*-
from app.custom.graphql import build_schema

schema = build_schema(["v1", "account"])
