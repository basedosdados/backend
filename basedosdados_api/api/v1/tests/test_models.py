# -*- coding: utf-8 -*-
import pytest
from django.core.exceptions import ValidationError

# from django.core.validators import RegexValidator

from basedosdados_api.api.v1.models import (
    Dataset,
    Area,
    Table,
    # Column,
    RawDataSource,
    InformationRequest,
    DateTimeRange,
    Analysis,
    CloudTable,
)


@pytest.mark.django_db
def test_invalid_area_slug_brasil():
    """Test for Area with dot names, which are invalid in slug."""
    area = Area(
        name="Brasil",
        slug="sa.br",
    )
    with pytest.raises(ValidationError):
        area.full_clean()


@pytest.mark.django_db
def test_invalid_organization(organizacao_bd):
    """Test for Organization."""
    with pytest.raises(ValidationError):
        organizacao_bd.full_clean()


@pytest.mark.django_db
def test_date_time_range(coverage_tabela):
    """Test for DateTimeRange."""
    date_time_range = DateTimeRange(
        coverage=coverage_tabela,
        start_year=2019,
        start_month=1,
        start_day=1,
        end_year=2022,
        end_month=6,
        interval=1,
    )
    date_time_range.full_clean()
    date_time_range.save()
    assert DateTimeRange.objects.exists()


@pytest.mark.django_db
def test_invalid_date_time_range(coverage_tabela):
    """Test for DateTimeRange."""
    date_time_range = DateTimeRange(
        coverage=coverage_tabela,
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
def test_create_dataset(
    dataset_dados_mestres, tema_saude, tema_educacao, tag_aborto, tag_covid
):
    """Test for Dataset."""
    dataset_dados_mestres.save()
    dataset_dados_mestres.themes.add(tema_saude, tema_educacao)
    dataset_dados_mestres.tags.add(tag_aborto, tag_covid)
    assert Dataset.objects.exists()


@pytest.mark.django_db
def test_create_table(tabela_bairros):
    """Test for Table."""
    tabela_bairros.save()
    assert Table.objects.exists()


@pytest.mark.django_db
def test_columns_create(
    coluna_state_id_bairros,
    coluna_nome_bairros,
    coluna_populacao_bairros,
):
    """Test for Column."""
    coluna_state_id_bairros.save()
    coluna_nome_bairros.save()
    coluna_populacao_bairros.save()

    tabela_bairros = Table.objects.get(slug="bairros")
    assert len(tabela_bairros.columns.all()) == 3


@pytest.mark.django_db
def test_create_rawdatasource(raw_data_source, entity_escola, entity_anual):
    """Test for RawDataSource."""
    raw_data_source.save()
    assert RawDataSource.objects.exists()


@pytest.mark.django_db
def test_create_information_request(pedido_informacao, entity_escola, entity_anual):
    """Test for InformationRequest."""
    pedido_informacao.save()

    assert InformationRequest.objects.exists()


@pytest.mark.django_db
def test_create_analysis(
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
def test_create_cloud_table(tabela_bairros):
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
