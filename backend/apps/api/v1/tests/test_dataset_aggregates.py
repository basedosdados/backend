# -*- coding: utf-8 -*-
"""Tests for the Dataset aggregate properties.

Every one of these properties rolls up the dataset's tables while excluding two
things: tables whose status is under_review or excluded, and the dictionary
tables (slug "dicionario" or "dictionary"). That exclusion is written out
longhand in roughly fifteen places, so it is exactly the kind of rule that drifts
in one copy without anyone noticing. These tests pin it down.

Dataset caches its table queryset with cached_property, so each test reloads the
dataset before reading a property.
"""

import pytest

from backend.apps.api.v1.models import (
    Coverage,
    Dataset,
    InformationRequest,
    RawDataSource,
    Status,
    Table,
)

MB = 1024 * 1024


@pytest.fixture(name="status_excluded")
def fixture_status_excluded():
    return Status.objects.create(name="Excluído", slug="excluded")


@pytest.fixture(name="status_under_review")
def fixture_status_under_review():
    return Status.objects.create(name="Em revisão", slug="under_review")


def add_table(dataset, slug, *, status=None, size=None, order=0, **kwargs):
    return Table.objects.create(
        dataset=dataset,
        slug=slug,
        name=slug,
        status=status,
        uncompressed_file_size=size,
        order=order,
        **kwargs,
    )


def reload(dataset):
    """Return a fresh instance, since the aggregates cache their queryset."""
    return Dataset.objects.get(pk=dataset.pk)


# ---------------------------------------------------------------------------
# The exclusion rule
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_counts_only_visible_tables(dataset_dados_mestres, status_excluded, status_under_review):
    add_table(dataset_dados_mestres, "visivel")
    add_table(dataset_dados_mestres, "excluida", status=status_excluded)
    add_table(dataset_dados_mestres, "em_revisao", status=status_under_review)
    assert reload(dataset_dados_mestres).n_tables == 1


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["dicionario", "dictionary"])
def test_dictionary_tables_are_excluded(dataset_dados_mestres, slug):
    add_table(dataset_dados_mestres, "visivel")
    add_table(dataset_dados_mestres, slug)
    assert reload(dataset_dados_mestres).n_tables == 1


@pytest.mark.django_db
def test_contains_tables_is_false_when_only_excluded_tables_exist(
    dataset_dados_mestres, status_excluded
):
    add_table(dataset_dados_mestres, "excluida", status=status_excluded)
    add_table(dataset_dados_mestres, "dicionario")
    dataset = reload(dataset_dados_mestres)
    assert dataset.contains_tables is False
    assert dataset.n_tables == 0


@pytest.mark.django_db
def test_contains_tables_is_true_with_one_visible_table(dataset_dados_mestres):
    add_table(dataset_dados_mestres, "visivel")
    assert reload(dataset_dados_mestres).contains_tables is True


@pytest.mark.django_db
def test_empty_dataset_reports_nothing(dataset_dados_mestres):
    dataset = reload(dataset_dados_mestres)
    assert dataset.contains_tables is False
    assert dataset.contains_raw_data_sources is False
    assert dataset.contains_information_requests is False
    assert dataset.n_tables == 0
    assert dataset.n_raw_data_sources == 0
    assert dataset.n_information_requests == 0
    assert dataset.first_table_id is None
    assert dataset.first_raw_data_source_id is None
    assert dataset.first_information_request_id is None


# ---------------------------------------------------------------------------
# Open and closed data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contains_open_data_follows_table_coverage(dataset_dados_mestres, area_br):
    table = add_table(dataset_dados_mestres, "aberta")
    Coverage.objects.create(table=table, area=area_br, is_closed=False)
    dataset = reload(dataset_dados_mestres)
    assert dataset.contains_open_data is True
    assert dataset.contains_closed_data is False


@pytest.mark.django_db
def test_contains_closed_data_follows_table_coverage(dataset_dados_mestres, area_br):
    table = add_table(dataset_dados_mestres, "fechada")
    Coverage.objects.create(table=table, area=area_br, is_closed=True)
    dataset = reload(dataset_dados_mestres)
    assert dataset.contains_closed_data is True
    assert dataset.contains_open_data is False


@pytest.mark.django_db
def test_open_data_on_an_excluded_table_does_not_count(
    dataset_dados_mestres, area_br, status_excluded
):
    table = add_table(dataset_dados_mestres, "excluida", status=status_excluded)
    Coverage.objects.create(table=table, area=area_br, is_closed=False)
    assert reload(dataset_dados_mestres).contains_open_data is False


@pytest.mark.django_db
def test_open_data_on_a_dictionary_table_does_not_count(dataset_dados_mestres, area_br):
    table = add_table(dataset_dados_mestres, "dicionario")
    Coverage.objects.create(table=table, area=area_br, is_closed=False)
    assert reload(dataset_dados_mestres).contains_open_data is False


@pytest.mark.django_db
def test_a_dataset_can_hold_both_open_and_closed_tables(dataset_dados_mestres, area_br):
    aberta = add_table(dataset_dados_mestres, "aberta")
    fechada = add_table(dataset_dados_mestres, "fechada", order=1)
    Coverage.objects.create(table=aberta, area=area_br, is_closed=False)
    Coverage.objects.create(table=fechada, area=area_br, is_closed=True)
    dataset = reload(dataset_dados_mestres)
    assert dataset.contains_open_data is True
    assert dataset.contains_closed_data is True


# ---------------------------------------------------------------------------
# Direct download, which is decided by file size
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_direct_download_counts_split_on_the_100mb_threshold(dataset_dados_mestres):
    add_table(dataset_dados_mestres, "pequena", size=50 * MB)
    add_table(dataset_dados_mestres, "grande", size=500 * MB, order=1)
    dataset = reload(dataset_dados_mestres)
    assert dataset.contains_direct_download_free == 1
    assert dataset.contains_direct_download_paid == 1


@pytest.mark.django_db
def test_a_table_without_a_size_counts_as_neither(dataset_dados_mestres):
    add_table(dataset_dados_mestres, "sem_tamanho", size=None)
    dataset = reload(dataset_dados_mestres)
    assert dataset.contains_direct_download_free == 0
    assert dataset.contains_direct_download_paid == 0


@pytest.mark.django_db
def test_a_large_table_is_closed_data(dataset_dados_mestres):
    """Between 100 MB and 1 GB a table counts as closed on size alone."""
    add_table(dataset_dados_mestres, "grande", size=500 * MB)
    assert reload(dataset_dados_mestres).contains_closed_data is True


# ---------------------------------------------------------------------------
# first_* pointers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_first_table_id_follows_order(dataset_dados_mestres):
    segunda = add_table(dataset_dados_mestres, "segunda", order=1)
    primeira = add_table(dataset_dados_mestres, "primeira", order=0)
    assert reload(dataset_dados_mestres).first_table_id == primeira.pk
    assert segunda.pk != primeira.pk


@pytest.mark.django_db
def test_first_table_id_skips_excluded_tables(dataset_dados_mestres, status_excluded):
    add_table(dataset_dados_mestres, "excluida", status=status_excluded, order=0)
    visivel = add_table(dataset_dados_mestres, "visivel", order=1)
    assert reload(dataset_dados_mestres).first_table_id == visivel.pk


@pytest.mark.django_db
def test_first_open_and_closed_table_ids(dataset_dados_mestres, area_br):
    fechada = add_table(dataset_dados_mestres, "fechada", order=0)
    aberta = add_table(dataset_dados_mestres, "aberta", order=1)
    Coverage.objects.create(table=fechada, area=area_br, is_closed=True)
    Coverage.objects.create(table=aberta, area=area_br, is_closed=False)
    dataset = reload(dataset_dados_mestres)
    assert dataset.first_open_table_id == aberta.pk
    assert dataset.first_closed_table_id == fechada.pk


@pytest.mark.django_db
def test_first_open_table_id_is_none_without_open_data(dataset_dados_mestres, area_br):
    fechada = add_table(dataset_dados_mestres, "fechada")
    Coverage.objects.create(table=fechada, area=area_br, is_closed=True)
    assert reload(dataset_dados_mestres).first_open_table_id is None


# ---------------------------------------------------------------------------
# Raw data sources and information requests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_raw_data_sources_are_counted_and_filtered(
    dataset_dados_mestres, disponibilidade_online, licenca_mit, status_excluded
):
    visivel = RawDataSource.objects.create(
        dataset=dataset_dados_mestres,
        availability=disponibilidade_online,
        license=licenca_mit,
        name="visivel",
        order=0,
    )
    RawDataSource.objects.create(
        dataset=dataset_dados_mestres,
        availability=disponibilidade_online,
        license=licenca_mit,
        name="excluida",
        status=status_excluded,
        order=1,
    )
    dataset = reload(dataset_dados_mestres)
    assert dataset.n_raw_data_sources == 1
    assert dataset.contains_raw_data_sources is True
    assert dataset.first_raw_data_source_id == visivel.pk


@pytest.mark.django_db
def test_information_requests_are_counted_and_filtered(
    dataset_dados_mestres, usuario_inicio, status_excluded
):
    visivel = InformationRequest.objects.create(
        dataset=dataset_dados_mestres, started_by=usuario_inicio, order=0
    )
    InformationRequest.objects.create(
        dataset=dataset_dados_mestres,
        started_by=usuario_inicio,
        status=status_excluded,
        order=1,
    )
    dataset = reload(dataset_dados_mestres)
    assert dataset.n_information_requests == 1
    assert dataset.contains_information_requests is True
    assert dataset.first_information_request_id == visivel.pk


# ---------------------------------------------------------------------------
# Slug, popularity, temporal coverage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_full_slug_is_prefixed_by_the_organization_area(dataset_dados_mestres):
    assert dataset_dados_mestres.full_slug == "sa_br_dados_mestres"


@pytest.mark.django_db
def test_full_slug_drops_an_unknown_area(dataset_dados_mestres, organizacao_bd, area_br):
    area_br.slug = "unknown"
    area_br.save()
    assert reload(dataset_dados_mestres).full_slug == "dados_mestres"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "page_views,expected",
    [(0, 0.0), (None, 0.0), (1, 0.0), (10, 1.0), (100, 2.0), (1000, 3.0)],
)
def test_popularity_is_log10_of_page_views(dataset_dados_mestres, page_views, expected):
    dataset_dados_mestres.page_views = page_views
    assert dataset_dados_mestres.popularity == expected


@pytest.mark.django_db
def test_temporal_coverage_is_empty_without_ranges(dataset_dados_mestres):
    add_table(dataset_dados_mestres, "sem_cobertura")
    assert reload(dataset_dados_mestres).temporal_coverage == ""


@pytest.mark.django_db
def test_temporal_coverage_spans_the_datasets_tables(
    dataset_dados_mestres, tabela_bairros, coverage_tabela_open, datetime_range_1
):
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    assert reload(dataset_dados_mestres).temporal_coverage == "2021-06 - 2023-06"


@pytest.mark.django_db
def test_spatial_coverage_unions_the_datasets_resources(
    dataset_dados_mestres, tabela_bairros, area_br
):
    Coverage.objects.create(table=tabela_bairros, area=area_br, is_closed=False)
    assert reload(dataset_dados_mestres).spatial_coverage == ["sa_br"]
