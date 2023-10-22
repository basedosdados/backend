# -*- coding: utf-8 -*-
"""
Pytest Django models tests.
"""
import json

import pytest
from django.core.exceptions import ValidationError

from apps.apps.api.v1.models import (  # Column,
    Analysis,
    Area,
    CloudTable,
    Dataset,
    DateTimeRange,
    InformationRequest,
    RawDataSource,
    Table,
)

# from django.core.validators import RegexValidator


@pytest.mark.django_db
def test_area_slug_brasil_invalid():
    """Test for Area with dot names, which are invalid in slug."""
    area = Area(
        name="Brasil",
        slug="sa.br",
    )
    with pytest.raises(ValidationError):
        area.full_clean()


@pytest.mark.django_db
def test_organization_invalid(organizacao_invalida):
    """Test for Organization without name."""
    with pytest.raises(ValidationError):
        organizacao_invalida.full_clean()


@pytest.mark.django_db
def test_date_time_range_open(coverage_tabela_open):
    """Test for open DateTimeRange."""
    date_time_range = DateTimeRange(
        coverage=coverage_tabela_open,
        start_year=2019,
        start_month=1,
        start_day=1,
        end_year=2022,
        end_month=6,
        interval=1,
    )
    date_time_range.full_clean()
    date_time_range.save()
    assert date_time_range.is_closed is False
    assert DateTimeRange.objects.exists()


@pytest.mark.django_db
def test_date_time_range_closed(coverage_tabela_open):
    """Test for closed DateTimeRange."""
    date_time_range = DateTimeRange(
        coverage=coverage_tabela_open,
        start_year=2019,
        start_month=1,
        start_day=1,
        end_year=2022,
        end_month=6,
        interval=1,
        is_closed=True,
    )
    date_time_range.full_clean()
    date_time_range.save()
    open_date_time_range = DateTimeRange.objects.first()
    assert open_date_time_range.is_closed is True


@pytest.mark.django_db
def test_date_time_range_invalid(coverage_tabela_open):
    """
    Test for invalid DateTimeRange.
    Must raise ValidationError because start_quarter is bigger than 4.
    """
    date_time_range = DateTimeRange(
        coverage=coverage_tabela_open,
        start_year=2019,
        start_month=1,
        start_quarter=5,
        start_day=1,
        end_year=2022,
        end_month=6,
        interval=0,
    )
    with pytest.raises(ValidationError):
        date_time_range.clean()


@pytest.mark.django_db
def test_date_time_range_empty(coverage_tabela_open):
    """
    Test for empty DateTimeRange.
    All fields must be empty, except coverage.
    """
    date_time_range = DateTimeRange(
        coverage=coverage_tabela_open,
    )
    date_time_range.save()
    assert DateTimeRange.objects.exists()


@pytest.mark.django_db
def test_dataset_create(dataset_dados_mestres, tema_saude, tema_educacao, tag_aborto, tag_covid):
    """Test for Dataset creation"""
    dataset_dados_mestres.save()
    dataset_dados_mestres.themes.add(tema_saude, tema_educacao)
    dataset_dados_mestres.tags.add(tag_aborto, tag_covid)
    assert Dataset.objects.exists()


@pytest.mark.django_db
def test_table_create(tabela_bairros):
    """Test for Table without closed data."""
    tabela_bairros.save()
    assert Table.objects.exists()
    assert tabela_bairros.contains_closed_data is False


@pytest.mark.django_db
def test_table_with_empty_coverage(tabela_bairros, coverage_tabela_open, datetime_range_empty):
    """
    Test for Table with Coverage containing no DateTimeRange.
    Coverage must be empty string.
    """
    tabela_bairros.save()
    coverage_tabela_open.save()
    datetime_range_empty.coverage = coverage_tabela_open
    datetime_range_empty.save()
    assert tabela_bairros.dataset.coverage == ""


@pytest.mark.django_db
def test_columns_create(
    coluna_state_id_bairros,
    coluna_nome_bairros,
    coluna_populacao_bairros,
):
    """Test for Column without coverage."""
    coluna_state_id_bairros.save()
    coluna_nome_bairros.save()
    coluna_populacao_bairros.save()

    tabela_bairros = Table.objects.get(slug="bairros")
    assert len(tabela_bairros.columns.all()) == 3


@pytest.mark.django_db
def test_columns_create_with_open_coverage(
    area_br,
    coluna_nome_bairros,
    coverage_tabela_open,
    datetime_range_1,
    datetime_range_3,
):
    """Test for Column with coverage with valid date time ranges and no closed data."""
    coluna_nome_bairros.save()
    coverage_tabela_open.save()

    datetime_range_1.area = area_br
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()

    datetime_range_3.area = area_br
    datetime_range_3.coverage = coverage_tabela_open
    datetime_range_3.save()

    tabela_bairros = Table.objects.get(slug="bairros")
    assert len(tabela_bairros.columns.all()) == 1
    assert tabela_bairros.contains_closed_data is False
    assert coluna_nome_bairros.is_closed is False


@pytest.mark.django_db
def test_rawdatasource_create(
    raw_data_source,
):
    """Test for RawDataSource."""
    raw_data_source.save()
    assert RawDataSource.objects.exists()


@pytest.mark.django_db
def test_information_request_create(
    pedido_informacao,
):
    """Test for InformationRequest."""
    pedido_informacao.save()

    assert InformationRequest.objects.exists()


@pytest.mark.django_db
def test_analysis_create(  # pylint: disable=too-many-arguments
    analise_bairros,
    dataset_dados_mestres,
    tema_saude,
    tema_educacao,
    tag_aborto,
    tag_covid,
    usuario_inicio,
):
    """Test for Analysis."""
    analise_bairros.datasets.add(dataset_dados_mestres)
    analise_bairros.themes.add(tema_saude, tema_educacao)
    analise_bairros.tags.add(tag_aborto, tag_covid)
    analise_bairros.authors.add(usuario_inicio)
    analise_bairros.save()

    assert Analysis.objects.exists()


@pytest.mark.django_db
def test_cloud_table_create(tabela_bairros):
    """Test for CloudTable."""
    cloud_table = CloudTable(
        table=tabela_bairros,
        gcp_project_id="basedosdados-dev",
        gcp_dataset_id="dados_mestres",
        gcp_table_id="bairros",
    )
    cloud_table.clean()
    cloud_table.save()

    assert CloudTable.objects.exists()


@pytest.mark.django_db
def test_table_with_multiple_coverages(
    tabela_bairros,
    coverage_tabela_open,
    coverage_tabela_closed,
    datetime_range_1,
    datetime_range_3,
):
    """Test for Dataset with multiple coverages."""
    tabela_bairros.save()
    coverage_tabela_open.save()
    coverage_tabela_closed.save()
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    datetime_range_3.coverage = coverage_tabela_closed
    datetime_range_3.save()
    tabela_bairros.coverages.add(coverage_tabela_open, coverage_tabela_closed)
    tabela_bairros.save()

    table_expected_coverage = [
        {"year": "2021", "month": "06", "day": None, "type": "open"},
        {"year": "2023", "month": "06", "day": None, "type": "open"},
        {"year": "2026", "month": "06", "day": None, "type": "closed"},
    ]

    assert tabela_bairros.full_coverage == json.dumps(table_expected_coverage)


@pytest.mark.django_db
def test_table_with_open_coverages(
    tabela_bairros,
    coverage_tabela_open,
    datetime_range_1,
):
    """Test for Dataset with multiple coverages."""
    tabela_bairros.save()
    coverage_tabela_open.save()
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    tabela_bairros.coverages.add(coverage_tabela_open)
    tabela_bairros.save()

    table_expected_coverage = [
        {"year": "2021", "month": "06", "day": None, "type": "open"},
        {"year": "2023", "month": "06", "day": None, "type": "open"},
    ]

    assert tabela_bairros.full_coverage == json.dumps(table_expected_coverage)


@pytest.mark.django_db
def test_table_with_closed_coverages(
    tabela_bairros,
    coverage_tabela_closed,
    datetime_range_3,
):
    """Test for Dataset with multiple coverages."""
    tabela_bairros.save()
    coverage_tabela_closed.save()
    datetime_range_3.coverage = coverage_tabela_closed
    datetime_range_3.save()
    tabela_bairros.coverages.add(coverage_tabela_closed)
    tabela_bairros.save()

    table_expected_coverage = [
        {"year": "2023", "month": "07", "day": None, "type": "closed"},
        {"year": "2026", "month": "06", "day": None, "type": "closed"},
    ]

    assert tabela_bairros.full_coverage == json.dumps(table_expected_coverage)
