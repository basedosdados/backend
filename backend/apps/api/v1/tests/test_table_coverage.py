# -*- coding: utf-8 -*-
"""
Pytest Django models tests.
"""

import pytest
from django.core.exceptions import ValidationError

from backend.apps.api.v1.models import Entity, EntityCategory, Table


@pytest.fixture(name="entity_category_datetime")
@pytest.mark.django_db
def fixture_entity_category_datetime():
    """EntityCategory matching Column.coverage_entity's limit_choices_to."""
    return EntityCategory.objects.create(slug="datetime", name="Data/Hora")


@pytest.fixture(name="entity_year")
@pytest.mark.django_db
def fixture_entity_year(entity_category_datetime):
    """Entity for the 'year' coverage role."""
    return Entity.objects.create(slug="year", name="Ano", category=entity_category_datetime)


@pytest.fixture(name="entity_month")
@pytest.mark.django_db
def fixture_entity_month(entity_category_datetime):
    """Entity for the 'month' coverage role."""
    return Entity.objects.create(slug="month", name="Mês", category=entity_category_datetime)


@pytest.mark.django_db
def test_table_coverage_with_no_date_time_range(
    tabela_bairros,
    coverage_tabela_open,
):
    """
    Test for validating a coverage with no datetime_range.
    """
    coverage_tabela_open.save()

    tabela_bairros.clean()
    tabela_bairros.save()

    assert Table.objects.exists()


@pytest.mark.django_db
def test_table_create_with_overlapping_coverage(
    tabela_pro,
    coverage_tabela_open,
    coverage_tabela_closed,
    datetime_range_1,
    datetime_range_2,
):
    """
    Test for Table with Coverage containing overlapping DateTimeRange.
    Overlapping DateTimeRange in the same Coverage area ust raise ValidationError.
    """
    tabela_pro.save()
    coverage_tabela_open.save()
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()

    datetime_range_2.coverage = coverage_tabela_closed
    datetime_range_2.save()
    with pytest.raises(ValidationError):
        tabela_pro.coverages.add(coverage_tabela_open, coverage_tabela_closed)
        tabela_pro.clean()


@pytest.mark.django_db
def test_coverage_columns_empty_when_no_column_tagged(tabela_bairros):
    """No column tagged with a coverage_entity: coverage_columns is empty,
    and clean() passes (e.g. non_historical, or not materialized yet)."""
    assert tabela_bairros.coverage_columns == []
    tabela_bairros.clean()


@pytest.mark.django_db
def test_coverage_entity_duplicate_role_raises(
    tabela_bairros,
    coluna_nome_bairros,
    coluna_populacao_bairros,
    entity_year,
):
    """Two columns tagged with the same coverage_entity (e.g. two 'year'
    columns) is a data problem — clean() must raise, not pick one."""
    coluna_nome_bairros.coverage_entity = entity_year
    coluna_nome_bairros.save()
    coluna_populacao_bairros.coverage_entity = entity_year
    coluna_populacao_bairros.save()

    with pytest.raises(ValidationError):
        tabela_bairros.clean()


@pytest.mark.django_db
def test_coverage_entity_invalid_combination_raises(
    tabela_bairros,
    coluna_nome_bairros,
    entity_month,
):
    """'month' alone (no 'year') isn't any valid coverage shape —
    clean() must raise."""
    coluna_nome_bairros.coverage_entity = entity_month
    coluna_nome_bairros.save()

    with pytest.raises(ValidationError):
        tabela_bairros.clean()


@pytest.mark.django_db
def test_coverage_entity_single_column_is_valid(
    tabela_bairros,
    coluna_nome_bairros,
    entity_year,
):
    """One column tagged 'year' alone passes clean() — a valid shape on its
    own, same as 'date' alone. A client derives the "kind" itself from
    which entity slugs are present; the backend only validates here."""
    coluna_nome_bairros.coverage_entity = entity_year
    coluna_nome_bairros.save()

    tabela_bairros.clean()
    assert tabela_bairros.coverage_columns == [coluna_nome_bairros.name]


@pytest.mark.django_db
def test_coverage_entity_two_columns_is_valid(
    tabela_bairros,
    coluna_nome_bairros,
    coluna_populacao_bairros,
    entity_year,
    entity_month,
):
    """'year' + 'month' together passes clean() — a valid shape."""
    coluna_nome_bairros.coverage_entity = entity_year
    coluna_nome_bairros.save()
    coluna_populacao_bairros.coverage_entity = entity_month
    coluna_populacao_bairros.save()

    tabela_bairros.clean()


@pytest.mark.django_db
def test_coverage_columns_property_returns_names_in_column_order(
    tabela_bairros,
    coluna_nome_bairros,
    coluna_populacao_bairros,
    entity_year,
    entity_month,
):
    """coverage_columns resolves live Column.name, in column order — never a
    duplicated string that could go stale if a column is renamed."""
    coluna_nome_bairros.coverage_entity = entity_year
    coluna_nome_bairros.order = 1
    coluna_nome_bairros.save()
    coluna_populacao_bairros.coverage_entity = entity_month
    coluna_populacao_bairros.order = 2
    coluna_populacao_bairros.save()

    assert tabela_bairros.coverage_columns == [
        coluna_nome_bairros.name,
        coluna_populacao_bairros.name,
    ]

    coluna_nome_bairros.name = "Nome do bairro (renomeado)"
    coluna_nome_bairros.save()

    assert tabela_bairros.coverage_columns[0] == "Nome do bairro (renomeado)"
