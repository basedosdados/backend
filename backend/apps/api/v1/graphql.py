# -*- coding: utf-8 -*-

from graphene import UUID, Boolean, Float, List, Mutation, ObjectType, String
from graphene_django import DjangoObjectType

from backend.apps.api.v1.models import ObservationLevel, Table, TableNeighbor
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


class ReorderTables(Mutation):
    """Set display order for tables within a dataset.
    ids: ordered list of table UUIDs (index 0 = first)."""

    class Arguments:
        ids = List(UUID, required=True)

    ok = Boolean()
    errors = List(String)

    def mutate(root, info, ids):
        if not info.context.user.is_staff:
            return ReorderTables(ok=False, errors=["Permission denied"])
        for i, table_id in enumerate(ids):
            Table.objects.filter(pk=table_id).update(order=i)
        return ReorderTables(ok=True, errors=[])


class ReorderObservationLevels(Mutation):
    """Set display order for observation levels within a table.
    ids: ordered list of ObservationLevel UUIDs (index 0 = first)."""

    class Arguments:
        ids = List(UUID, required=True)

    ok = Boolean()
    errors = List(String)

    def mutate(root, info, ids):
        if not info.context.user.is_staff:
            return ReorderObservationLevels(ok=False, errors=["Permission denied"])
        for i, ol_id in enumerate(ids):
            ObservationLevel.objects.filter(pk=ol_id).update(order=i)
        return ReorderObservationLevels(ok=True, errors=[])


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


class APIMutation:
    reorder_tables = ReorderTables.Field()
    reorder_observation_levels = ReorderObservationLevels.Field()
