# -*- coding: utf-8 -*-

from graphene import UUID, Boolean, Float, List, ObjectType, String
from graphene_django import DjangoObjectType

from backend.apps.api.v1.models import Table, TableNeighbor
from backend.apps.api.v1.sql_generator import OneBigTableQueryGenerator
from backend.custom.graphql_base import PlainTextNode


class TableNeighborNode(DjangoObjectType):
    """Similiar tables and columns with filters"""

    table_id = String()
    table_name = String()
    dataset_id = String()
    dataset_name = String()
    score = Float()

    class Meta:
        model = TableNeighbor
        fields = ("id",)
        filter_fields = ("id",)
        interfaces = (PlainTextNode,)

    def resolve__table_id(root, info):
        return root.table_b.pk

    def resolve__table_name(root, info):
        return root.table_b.name

    def resolve__dataset_id(root, info):
        return root.table_b.dataset.pk

    def resolve__dataset_name(root, info):
        return root.table_b.dataset.name

    def resolve_score(root, info):
        return root.score


class Query(ObjectType):
    get_table_neighbor = List(
        TableNeighborNode,
        table_id=UUID(required=True),
        theme=String(),
        share_theme=Boolean(),
    )
    get_table_one_big_table_query = String(
        table_id=UUID(required=True),
        columns=List(String),
        include_table_translation=Boolean(),
    )

    def resolve_get_table_neighbor(root, info, table_id, **kwargs):
        return TableNeighbor.objects.filter(table_a__pk=table_id).all()

    def resolve_get_table_one_big_table_query(
        root, info, table_id, columns=None, include_table_translation=True, **kwargs
    ):
        if table := Table.objects.filter(pk=table_id).first():
            sql_query = OneBigTableQueryGenerator().generate(
                table, columns, include_table_translation
            )
            return sql_query
