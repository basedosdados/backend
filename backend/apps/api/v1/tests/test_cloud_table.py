# -*- coding: utf-8 -*-
"""Tests for CloudTable validation and the Table slug properties derived from it."""

import pytest
from django.core.exceptions import ValidationError

from backend.apps.api.v1.models import CloudTable


def build(table, **overrides):
    fields = {
        "table": table,
        "gcp_project_id": "basedosdados-dev",
        "gcp_dataset_id": "mundo_transferwise",
        "gcp_table_id": "taxa_cambio",
    }
    fields.update(overrides)
    return CloudTable.objects.create(**fields)


@pytest.mark.django_db
def test_valid_identifiers_pass(tabela_bairros):
    cloud_table = build(tabela_bairros)
    cloud_table.clean()
    assert str(cloud_table) == "basedosdados-dev.mundo_transferwise.taxa_cambio"


@pytest.mark.django_db
def test_project_id_must_be_kebab_case(tabela_bairros):
    cloud_table = build(tabela_bairros, gcp_project_id="base_dos_dados")
    with pytest.raises(ValidationError) as exc:
        cloud_table.clean()
    assert "gcp_project_id" in exc.value.message_dict


@pytest.mark.django_db
def test_dataset_id_must_be_snake_case(tabela_bairros):
    cloud_table = build(tabela_bairros, gcp_dataset_id="mundo-transferwise")
    with pytest.raises(ValidationError) as exc:
        cloud_table.clean()
    assert "gcp_dataset_id" in exc.value.message_dict


@pytest.mark.django_db
def test_table_id_must_be_snake_case(tabela_bairros):
    cloud_table = build(tabela_bairros, gcp_table_id="Taxa-Cambio")
    with pytest.raises(ValidationError) as exc:
        cloud_table.clean()
    assert "gcp_table_id" in exc.value.message_dict


@pytest.mark.django_db
def test_dataset_id_is_validated_even_without_a_project_id(tabela_bairros):
    """Each identifier is guarded by its own value.

    The dataset check previously keyed off gcp_project_id, so a malformed dataset
    id passed validation whenever the project id happened to be blank.
    """
    cloud_table = build(tabela_bairros, gcp_project_id="", gcp_dataset_id="Mundo-Transferwise")
    with pytest.raises(ValidationError) as exc:
        cloud_table.clean()
    assert "gcp_dataset_id" in exc.value.message_dict


@pytest.mark.django_db
def test_blank_identifiers_are_skipped(tabela_bairros):
    """Blank is handled by the field's own required/blank rules, not by the case check."""
    cloud_table = build(tabela_bairros, gcp_project_id="", gcp_dataset_id="", gcp_table_id="")
    cloud_table.clean()


@pytest.mark.django_db
def test_columns_must_belong_to_the_same_table(tabela_bairros, tabela_pro, coluna_nome_bairros):
    cloud_table = build(tabela_pro)
    cloud_table.columns.add(coluna_nome_bairros)
    with pytest.raises(ValidationError) as exc:
        cloud_table.clean()
    assert "columns" in exc.value.message_dict


@pytest.mark.django_db
def test_all_errors_are_reported_together(tabela_bairros):
    cloud_table = build(
        tabela_bairros,
        gcp_project_id="Base_Dos_Dados",
        gcp_dataset_id="Mundo-Transferwise",
        gcp_table_id="Taxa-Cambio",
    )
    with pytest.raises(ValidationError) as exc:
        cloud_table.clean()
    assert set(exc.value.message_dict) == {
        "gcp_project_id",
        "gcp_dataset_id",
        "gcp_table_id",
    }


@pytest.mark.django_db
def test_table_slugs_derive_from_the_first_cloud_table(tabela_bairros):
    build(tabela_bairros)
    assert tabela_bairros.gbq_slug == "basedosdados.mundo_transferwise.taxa_cambio"
    assert tabela_bairros.gbq_dict_slug == "basedosdados.mundo_transferwise.dicionario"
    assert tabela_bairros.gbq_table_slug == "taxa_cambio"
    assert tabela_bairros.gcs_slug == "staging/mundo_transferwise/taxa_cambio"


@pytest.mark.django_db
def test_table_slugs_are_none_without_a_cloud_table(tabela_bairros):
    assert tabela_bairros.gbq_slug is None
    assert tabela_bairros.gbq_dict_slug is None
    assert tabela_bairros.gbq_table_slug is None
    assert tabela_bairros.gcs_slug is None
