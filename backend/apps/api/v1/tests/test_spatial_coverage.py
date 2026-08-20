# -*- coding: utf-8 -*-
"""Tests for spatial coverage aggregation.

get_spatial_coverage collapses the areas of a resource's coverages to the highest
level in each branch of the area hierarchy. The rules are stated in its docstring
but were not exercised anywhere; these tests turn that docstring into a contract.
"""

import pytest

from backend.apps.api.v1.models import Area, Coverage, get_spatial_coverage


def cover(table, *slugs):
    """Attach one coverage per area slug to a table."""
    for slug in slugs:
        area, _ = Area.objects.get_or_create(slug=slug)
        Coverage.objects.create(table=table, area=area, is_closed=False)


@pytest.mark.django_db
def test_no_areas_returns_empty_list(tabela_bairros):
    assert get_spatial_coverage([tabela_bairros]) == []


@pytest.mark.django_db
def test_coverage_without_area_is_ignored(tabela_bairros):
    Coverage.objects.create(table=tabela_bairros, is_closed=False)
    assert get_spatial_coverage([tabela_bairros]) == []


@pytest.mark.django_db
def test_duplicate_areas_are_deduplicated(tabela_bairros):
    cover(tabela_bairros, "br_mg_3100104", "br_mg_3100104")
    assert get_spatial_coverage([tabela_bairros]) == ["br_mg_3100104"]


@pytest.mark.django_db
def test_sibling_areas_are_both_kept(tabela_bairros):
    cover(tabela_bairros, "br_mg_3100104", "br_sp_3500105")
    assert get_spatial_coverage([tabela_bairros]) == ["br_mg_3100104", "br_sp_3500105"]


@pytest.mark.django_db
def test_child_is_dropped_when_its_parent_is_present(tabela_bairros):
    """br_mg has no parent in the set and survives; us_ny is covered by us."""
    cover(tabela_bairros, "br_mg", "us_ny", "us")
    assert get_spatial_coverage([tabela_bairros]) == ["br_mg", "us"]


@pytest.mark.django_db
def test_world_absorbs_everything(tabela_bairros):
    cover(tabela_bairros, "br_mg", "world", "us")
    assert get_spatial_coverage([tabela_bairros]) == ["world"]


@pytest.mark.django_db
def test_grandparent_absorbs_grandchild(tabela_bairros):
    cover(tabela_bairros, "br", "br_mg_3100104")
    assert get_spatial_coverage([tabela_bairros]) == ["br"]


@pytest.mark.django_db
def test_result_is_sorted(tabela_bairros):
    cover(tabela_bairros, "us_ny", "br_sp", "ar_ba")
    assert get_spatial_coverage([tabela_bairros]) == ["ar_ba", "br_sp", "us_ny"]


@pytest.mark.django_db
def test_areas_are_unioned_across_resources(tabela_bairros, tabela_pro):
    cover(tabela_bairros, "br_mg")
    cover(tabela_pro, "br_sp")
    assert get_spatial_coverage([tabela_bairros, tabela_pro]) == ["br_mg", "br_sp"]


@pytest.mark.django_db
def test_parent_in_a_second_resource_still_absorbs_the_child(tabela_bairros, tabela_pro):
    """The hierarchy is collapsed over the union, not per resource."""
    cover(tabela_bairros, "br_mg_3100104")
    cover(tabela_pro, "br_mg")
    assert get_spatial_coverage([tabela_bairros, tabela_pro]) == ["br_mg"]


@pytest.mark.django_db
def test_table_property_matches_the_helper(tabela_bairros):
    cover(tabela_bairros, "br_mg", "br_mg_3100104")
    assert tabela_bairros.spatial_coverage == ["br_mg"]


@pytest.mark.django_db
def test_column_falls_back_to_its_table(tabela_bairros, coluna_nome_bairros):
    """A column with no area of its own reports the table's coverage."""
    cover(tabela_bairros, "br_sp")
    assert coluna_nome_bairros.spatial_coverage == ["br_sp"]


@pytest.mark.django_db
def test_column_area_overrides_the_table(tabela_bairros, coluna_nome_bairros):
    cover(tabela_bairros, "br_sp")
    area, _ = Area.objects.get_or_create(slug="br_mg")
    Coverage.objects.create(column=coluna_nome_bairros, area=area, is_closed=False)
    assert coluna_nome_bairros.spatial_coverage == ["br_mg"]
