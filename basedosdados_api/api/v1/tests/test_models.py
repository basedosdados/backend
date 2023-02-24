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
)


@pytest.mark.django_db
def test_invalid_area_slug_brasil():
    """Test for Area with dot names, which are invalid in slug."""
    area = Area(
        slug="sa.br",
    )
    with pytest.raises(ValidationError):
        area.full_clean()


@pytest.mark.django_db
def test_invalid_area_key():
    """Test for Area with dot names, which are invalid in slug."""
    area = Area(
        key="SA.br",
    )
    with pytest.raises(ValidationError):
        area.full_clean()


@pytest.mark.django_db
def test_area_key_not_in_bd_dict():
    """Test for Area with dot names, which are invalid in slug."""
    area = Area(
        slug="brasil",
        key="na.br",
    )
    with pytest.raises(ValidationError):
        area.full_clean()


@pytest.mark.django_db
def test_valid_area_key():
    """Test for Area with dot names, which are invalid in slug."""
    area = Area(
        slug="brasil",
        key="sa.br",
    )
    area.full_clean()
    area.save()
    assert Area.objects.exists()


@pytest.mark.django_db
def test_invalid_organization(organizacao_bd):
    """Test for Organization."""
    with pytest.raises(ValidationError):
        organizacao_bd.full_clean()


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
def test_create_table(tabela_bairros, observation_level_anual):
    """Test for Table."""
    tabela_bairros.save()
    tabela_bairros.observation_level.add(observation_level_anual)
    assert Table.objects.exists()
    assert len(tabela_bairros.observation_level.all()) == 1


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
    raw_data_source.entities.add(entity_escola, entity_anual)
    assert raw_data_source.entities.count() == 2
    assert RawDataSource.objects.exists()


@pytest.mark.django_db
def test_create_information_request(pedido_informacao, entity_escola, entity_anual):
    """Test for InformationRequest."""
    pedido_informacao.save()
    pedido_informacao.entities.add(entity_escola, entity_anual)

    assert pedido_informacao.entities.count() == 2
    assert InformationRequest.objects.exists()
