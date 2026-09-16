# -*- coding: utf-8 -*-
"""Tests for Table and Column relational logic.

Covers the overlap check in Table.clean, the similarity scores that drive the
"related tables" feature, the directory-key constraint on Column, and the
author/cleaner payloads the frontend renders.
"""

import pytest
from django.core.exceptions import ValidationError

from backend.apps.api.v1.models import (
    Area,
    Coverage,
    DateTimeRange,
    Table,
    TableNeighbor,
)


def covered(table, area, *, start, end, is_closed=False):
    coverage = Coverage.objects.create(table=table, area=area, is_closed=is_closed)
    DateTimeRange.objects.create(
        coverage=coverage, start_year=start, end_year=end, start_month=1, end_month=1, interval=1
    )
    return coverage


# ---------------------------------------------------------------------------
# Table.clean: coverages must not overlap within an area
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_disjoint_coverages_in_one_area_are_fine(tabela_bairros, area_br):
    covered(tabela_bairros, area_br, start=2018, end=2020)
    covered(tabela_bairros, area_br, start=2021, end=2023)
    tabela_bairros.clean()


@pytest.mark.django_db
def test_overlapping_coverages_in_one_area_are_rejected(tabela_bairros, area_br):
    covered(tabela_bairros, area_br, start=2018, end=2022)
    covered(tabela_bairros, area_br, start=2021, end=2023)
    with pytest.raises(ValidationError) as exc:
        tabela_bairros.clean()
    assert "coverages_areas" in exc.value.message_dict


@pytest.mark.django_db
def test_overlaps_in_different_areas_are_fine(tabela_bairros, area_br):
    """The check is per area, so two regions may cover the same years."""
    outra = Area.objects.create(slug="ar", name="Argentina")
    covered(tabela_bairros, area_br, start=2018, end=2022)
    covered(tabela_bairros, outra, start=2018, end=2022)
    tabela_bairros.clean()


@pytest.mark.django_db
def test_a_table_with_no_coverages_cleans(tabela_bairros):
    tabela_bairros.clean()


@pytest.mark.django_db
def test_a_coverage_without_an_area_is_skipped(tabela_bairros):
    Coverage.objects.create(table=tabela_bairros, is_closed=False)
    tabela_bairros.clean()


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_area_similarity_is_one_for_matching_areas(tabela_bairros, tabela_pro, area_br):
    Coverage.objects.create(table=tabela_bairros, area=area_br, is_closed=False)
    Coverage.objects.create(table=tabela_pro, area=area_br, is_closed=False)
    assert tabela_bairros.get_similarity_of_area(tabela_pro) == 1


@pytest.mark.django_db
def test_area_similarity_is_zero_for_unrelated_areas(tabela_bairros, tabela_pro):
    brasil = Area.objects.create(slug="br", name="Brasil")
    argentina = Area.objects.create(slug="ar", name="Argentina")
    Coverage.objects.create(table=tabela_bairros, area=brasil, is_closed=False)
    Coverage.objects.create(table=tabela_pro, area=argentina, is_closed=False)
    assert tabela_bairros.get_similarity_of_area(tabela_pro) == 0


@pytest.mark.django_db
def test_an_area_with_a_blank_name_matches_every_other_area(tabela_bairros, tabela_pro):
    """Recorded, not endorsed: the comparison is a prefix test on Area.name.

    Every string starts with "", so an Area saved without a name scores as
    similar to all of them and inflates the related-tables ranking. Area.name is
    declared blank=False, so full_clean() would reject one — but the similarity
    code is reached from rows created without validation.
    """
    unnamed = Area.objects.create(slug="sem_nome", name="")
    argentina = Area.objects.create(slug="ar", name="Argentina")
    Coverage.objects.create(table=tabela_bairros, area=unnamed, is_closed=False)
    Coverage.objects.create(table=tabela_pro, area=argentina, is_closed=False)
    assert tabela_bairros.get_similarity_of_area(tabela_pro) == 1


@pytest.mark.django_db
def test_similarity_without_coverages_is_zero_rather_than_a_division_error(
    tabela_bairros, tabela_pro
):
    assert tabela_bairros.get_similarity_of_area(tabela_pro) == 0
    assert tabela_bairros.get_similarity_of_datetime(tabela_pro) == 0


@pytest.mark.django_db
def test_datetime_similarity_is_one_for_overlapping_ranges(tabela_bairros, tabela_pro, area_br):
    covered(tabela_bairros, area_br, start=2018, end=2022)
    covered(tabela_pro, area_br, start=2021, end=2024)
    assert tabela_bairros.get_similarity_of_datetime(tabela_pro) == 1


@pytest.mark.django_db
def test_directory_similarity_counts_shared_directory_keys(
    tabela_bairros,
    tabela_pro,
    coluna_state_id_bairros,
    coluna_state_id_diretorio,
    bigquery_type_string,
):
    from backend.apps.api.v1.models import Column

    Column.objects.create(
        table=tabela_pro,
        name="ID do estado",
        bigquery_type=bigquery_type_string,
        directory_primary_key=coluna_state_id_diretorio,
        order=1,
    )
    ratio, shared = tabela_bairros.get_similarity_of_directory(tabela_pro)
    assert ratio == 1
    assert shared == {coluna_state_id_diretorio}


@pytest.mark.django_db
def test_directory_similarity_is_zero_without_a_shared_key(
    tabela_bairros, tabela_pro, coluna_state_id_bairros
):
    ratio, shared = tabela_bairros.get_similarity_of_directory(tabela_pro)
    assert ratio == 0
    assert shared == set()


# ---------------------------------------------------------------------------
# TableNeighbor
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_table_cannot_neighbour_itself(tabela_bairros):
    neighbor = TableNeighbor(table_a=tabela_bairros, table_b=tabela_bairros)
    with pytest.raises(ValidationError) as exc:
        neighbor.clean()
    assert set(exc.value.message_dict) == {"table_a", "table_b"}


@pytest.mark.django_db
def test_two_different_tables_may_be_neighbours(tabela_bairros, tabela_pro):
    TableNeighbor(table_a=tabela_bairros, table_b=tabela_pro).clean()


@pytest.mark.django_db
def test_the_neighbour_score_sums_the_rounded_components(tabela_bairros, tabela_pro):
    neighbor = TableNeighbor.objects.create(
        table_a=tabela_bairros,
        table_b=tabela_pro,
        similarity_of_directory=0.666,
        similarity_of_popularity=0.334,
    )
    assert neighbor.score == pytest.approx(1.0)


@pytest.mark.django_db
def test_the_neighbour_payload_describes_the_other_table(tabela_bairros, tabela_pro):
    neighbor = TableNeighbor.objects.create(
        table_a=tabela_bairros,
        table_b=tabela_pro,
        similarity_of_directory=0.5,
        similarity_of_popularity=0.25,
    )
    payload = neighbor.as_dict
    assert payload["table_id"] == str(tabela_pro.pk)
    assert payload["table_name"] == tabela_pro.name
    assert payload["dataset_id"] == str(tabela_pro.dataset.pk)


# ---------------------------------------------------------------------------
# Column.clean
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_directory_key_must_live_in_a_directory_table(
    tabela_bairros, coluna_nome_bairros, coluna_populacao_bairros
):
    """coluna_populacao_bairros belongs to a table with is_directory=False."""
    coluna_nome_bairros.directory_primary_key = coluna_populacao_bairros
    with pytest.raises(ValidationError) as exc:
        coluna_nome_bairros.clean()
    assert "directory_primary_key" in exc.value.message_dict


@pytest.mark.django_db
def test_a_directory_key_in_a_directory_table_is_accepted(
    coluna_state_id_bairros, coluna_state_id_diretorio
):
    coluna_state_id_bairros.clean()


@pytest.mark.django_db
def test_an_observation_level_must_belong_to_the_same_table(
    coluna_nome_bairros, tabela_pro, entity_anual
):
    from backend.apps.api.v1.models import ObservationLevel

    observation = ObservationLevel.objects.create(entity=entity_anual, table=tabela_pro)
    coluna_nome_bairros.observation_level = observation
    with pytest.raises(ValidationError) as exc:
        coluna_nome_bairros.clean()
    assert "observation_level" in exc.value.message_dict


@pytest.mark.django_db
def test_a_column_without_extras_cleans(coluna_populacao_bairros):
    coluna_populacao_bairros.clean()


# ---------------------------------------------------------------------------
# Author payloads
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_author_payloads_are_empty_without_authors(tabela_bairros):
    assert tabela_bairros.published_by_info == []
    assert tabela_bairros.data_cleaned_by_info == []


@pytest.mark.django_db
def test_the_author_payload_carries_the_public_profile(tabela_bairros, usuario_inicio):
    usuario_inicio.github = "https://github.com/usuario"
    usuario_inicio.website = "https://usuario.dev"
    usuario_inicio.save()
    tabela_bairros.published_by.add(usuario_inicio)

    payload = tabela_bairros.published_by_info
    assert payload == [
        {
            "firstName": "Usuario",
            "lastName": "Inicio",
            "email": "usuario@usuario.com",
            "github": "https://github.com/usuario",
            "twitter": usuario_inicio.twitter,
            "website": "https://usuario.dev",
        }
    ]


@pytest.mark.django_db
def test_the_cleaner_payload_uses_the_same_shape(tabela_bairros, usuario_inicio):
    tabela_bairros.data_cleaned_by.add(usuario_inicio)
    assert tabela_bairros.data_cleaned_by_info[0]["email"] == "usuario@usuario.com"


# ---------------------------------------------------------------------------
# Partitions and coverage units
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_partitions_lists_only_partition_columns(
    tabela_bairros, coluna_nome_bairros, coluna_populacao_bairros
):
    assert tabela_bairros.partitions == ""
    coluna_populacao_bairros.is_partition = True
    coluna_populacao_bairros.save()
    assert Table.objects.get(pk=tabela_bairros.pk).partitions == "População"


@pytest.mark.django_db
def test_coverage_datetime_units_is_none_without_units(tabela_bairros, coverage_tabela_open):
    assert tabela_bairros.coverage_datetime_units is None
