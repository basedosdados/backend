# -*- coding: utf-8 -*-
from graphene import Schema

from basedosdados_api.custom.graphql import build_query_schema

schema = Schema(
    query=build_query_schema("v1"),
)
