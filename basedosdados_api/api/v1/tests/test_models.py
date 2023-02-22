import pytest
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from basedosdados_api.api.v1.models import Dataset, Area, Table, Column


@pytest.mark.django_db
def test_invalid_area_brasil():
    """Test for Area with dot names, which are invalid in slug."""
    area = Area(
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
def test_create_dataset(
    dataset_dados_mestres,
    tema_saude, tema_educacao,
    tag_aborto, tag_covid
):
    """Test for Dataset."""
    dataset_dados_mestres.save()
    dataset_dados_mestres.themes.add(tema_saude, tema_educacao)
    dataset_dados_mestres.tags.add(tag_aborto, tag_covid)
    assert Dataset.objects.exists()


@pytest.mark.django_db
def test_create_table(
    tabela_bairros,
    observation_level_anual
):
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
