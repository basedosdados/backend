# -*- coding: utf-8 -*-

from graphene import UUID, Boolean, Field, Float, List, Mutation, ObjectType, String
from graphene_django import DjangoObjectType

from backend.apps.api.v1.models import (
    CloudTable,
    Column,
    ObservationLevel,
    Table,
    TableNeighbor,
)
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


class CoverageColumnType(ObjectType):
    """One column that defines part of a table's temporal coverage."""

    name = String()
    entity = String(description="coverage_entity slug, e.g. 'year', 'month'.")


#: Entity slug sets -> the shape name a pipeline's CoverageSpec needs
#: (its date_column kind). Mirrors Table._VALID_COVERAGE_ENTITY_SETS —
#: duplicated here (not imported) because naming the shape is a GraphQL
#: response-shaping concern, not something the model needs to validate.
_DATE_COLUMN_KIND_BY_ENTITY_SLUGS = {
    frozenset({"date"}): "date",
    frozenset({"year"}): "year",
    frozenset({"year", "month"}): "year_month",
    frozenset({"year", "quarter"}): "year_quarter",
    frozenset({"year", "bimester"}): "year_bimester",
}


class CoverageSpecType(ObjectType):
    """Everything a pipeline needs to build its own CoverageSpec for a
    table, from just dataset_id/table_id — no Table UUID required.

    Attributes:
        tier: one of "all_free", "all_bdpro", "part_bdpro",
            "non_historical", or "" (coverage_columns is non-empty but
            no Coverage exists yet).
        date_column_kind: the shape of coverage_columns, e.g.
            "year_month", or "" if coverage_columns is empty or matches
            no known shape.
        coverage_columns: the table's columns tagged with a
            coverage_entity, in column order.
    """

    tier = String()
    date_column_kind = String()
    coverage_columns = List(CoverageColumnType)


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
    coverage_spec = Field(
        CoverageSpecType,
        dataset_id=String(required=True),
        table_id=String(required=True),
        description="Resolves a table by its GCP dataset_id/table_id (not "
        "the Table UUID) and returns its coverage_columns and derived tier. "
        "Null if no CloudTable matches those ids.",
    )

    def resolve_get_table_neighbor(root, info, table_id, **kwargs):
        return TableNeighbor.objects.filter(table_a__pk=table_id).all()

    def resolve_coverage_spec(root, info, dataset_id, table_id, **kwargs):
        """Resolves coverageSpec for a table identified by its BigQuery ids.

        Args:
            dataset_id: BigQuery dataset id (CloudTable.gcp_dataset_id).
            table_id: BigQuery table id (CloudTable.gcp_table_id).

        Returns:
            A CoverageSpecType, or None if no CloudTable matches those ids.
        """
        cloud_table = CloudTable.objects.filter(
            gcp_dataset_id=dataset_id, gcp_table_id=table_id
        ).select_related("table")
        cloud_table = cloud_table.first()
        if cloud_table is None:
            return None
        table = cloud_table.table

        coverage_columns = [
            CoverageColumnType(name=col.name, entity=col.coverage_entity.slug)
            for col in table.columns.filter(coverage_entity__isnull=False)
            .select_related("coverage_entity")
            .order_by("order")
        ]

        if not coverage_columns:
            tier = "non_historical"
        else:
            has_free = table.coverages.filter(is_closed=False).exists()
            has_closed = table.coverages.filter(is_closed=True).exists()
            if has_free and has_closed:
                tier = "part_bdpro"
            elif has_free:
                tier = "all_free"
            elif has_closed:
                tier = "all_bdpro"
            else:
                tier = ""

        entity_slugs = frozenset(col.entity for col in coverage_columns)
        date_column_kind = _DATE_COLUMN_KIND_BY_ENTITY_SLUGS.get(entity_slugs, "")

        return CoverageSpecType(
            tier=tier,
            date_column_kind=date_column_kind,
            coverage_columns=coverage_columns,
        )

    def resolve_get_table_one_big_table_query(
        root, info, table_id, columns=None, include_table_translation=True, **kwargs
    ):
        if table := Table.objects.filter(pk=table_id).first():
            sql_query = OneBigTableQueryGenerator().generate(
                table, columns, include_table_translation
            )
            return sql_query


class ReorderColumns(Mutation):
    """Set display order for columns within a table.
    ids: ordered list of Column UUIDs (index 0 = first)."""

    class Arguments:
        ids = List(UUID, required=True)

    ok = Boolean()
    errors = List(String)

    def mutate(root, info, ids):
        if not info.context.user.is_staff:
            return ReorderColumns(ok=False, errors=["Permission denied"])
        for i, col_id in enumerate(ids):
            Column.objects.filter(pk=col_id).update(order=i)
        return ReorderColumns(ok=True, errors=[])


class APIMutation:
    reorder_tables = ReorderTables.Field()
    reorder_observation_levels = ReorderObservationLevels.Field()
    reorder_columns = ReorderColumns.Field()
