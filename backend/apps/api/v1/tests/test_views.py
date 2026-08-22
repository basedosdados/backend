# -*- coding: utf-8 -*-
"""Tests for the api/v1 REST endpoints.

table_stats feeds the public "how much data is there" counters, columns_view
backs the table page, and DatasetRedirectView keeps old dataset links alive.
None of the three had coverage.
"""

import json

import pytest
from django.test.client import Client

from backend.apps.api.v1.models import CloudTable, Status, Table

MB = 1024 * 1024
HOST = "localhost:8080"


@pytest.fixture(name="status_excluded")
def fixture_status_excluded():
    return Status.objects.create(name="Excluído", slug="excluded")


# ---------------------------------------------------------------------------
# table_stats
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_table_stats_on_an_empty_database(client: Client):
    response = client.get("/tables/stats/")
    assert response.status_code == 200
    assert response.json() == {
        "datasets_with_treated_tables": 0,
        "total_treated_tables": 0,
        "updated_last_30_days": 0,
        "total_size_bytes": 0,
        "total_rows": 0,
    }


@pytest.mark.django_db
def test_table_stats_counts_and_sums_visible_tables(client: Client, tabela_bairros):
    data = client.get("/tables/stats/").json()
    assert data["total_treated_tables"] == 1
    assert data["datasets_with_treated_tables"] == 1
    assert data["total_size_bytes"] == 1000
    assert data["total_rows"] == 100


@pytest.mark.django_db
def test_table_stats_applies_the_same_exclusions_as_the_dataset_aggregates(
    client: Client, dataset_dados_mestres, status_excluded
):
    Table.objects.create(dataset=dataset_dados_mestres, slug="visivel", name="v", order=0)
    Table.objects.create(
        dataset=dataset_dados_mestres, slug="oculta", name="o", status=status_excluded, order=1
    )
    Table.objects.create(dataset=dataset_dados_mestres, slug="dicionario", name="d", order=2)
    assert client.get("/tables/stats/").json()["total_treated_tables"] == 1


@pytest.mark.django_db
def test_table_stats_sums_across_tables(client: Client, dataset_dados_mestres):
    Table.objects.create(
        dataset=dataset_dados_mestres,
        slug="a",
        name="a",
        uncompressed_file_size=10 * MB,
        number_rows=5,
        order=0,
    )
    Table.objects.create(
        dataset=dataset_dados_mestres,
        slug="b",
        name="b",
        uncompressed_file_size=20 * MB,
        number_rows=7,
        order=1,
    )
    data = client.get("/tables/stats/").json()
    assert data["total_size_bytes"] == 30 * MB
    assert data["total_rows"] == 12


# ---------------------------------------------------------------------------
# columns_view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_single_column_is_serialised(client: Client, coluna_nome_bairros):
    response = client.get(f"/columns/{coluna_nome_bairros.id}/")
    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload[0]["fields"]["name"] == "Nome do bairro"


@pytest.mark.django_db
def test_an_unknown_column_is_a_404(client: Client):
    response = client.get("/columns/00000000-0000-0000-0000-000000000000/")
    assert response.status_code == 404
    assert response.json() == {"error": "Column not found"}


@pytest.mark.django_db
def test_a_tables_columns_come_back_in_order(
    client: Client, tabela_bairros, coluna_nome_bairros, coluna_populacao_bairros
):
    response = client.get(f"/tables/{tabela_bairros.id}/columns/")
    assert response.status_code == 200
    payload = response.json()
    assert [c["name"] for c in payload] == ["Nome do bairro", "População"]
    assert [c["order"] for c in payload] == [2, 3]


@pytest.mark.django_db
def test_a_table_without_columns_is_a_404(client: Client, tabela_bairros):
    response = client.get(f"/tables/{tabela_bairros.id}/columns/")
    assert response.status_code == 404
    assert response.json() == {"error": "Table not found or has no columns"}


@pytest.mark.django_db
def test_a_column_reports_its_own_temporal_coverage(
    client: Client,
    tabela_bairros,
    coluna_nome_bairros,
    coverage_coluna_open,
    datetime_range_2,
):
    datetime_range_2.coverage = coverage_coluna_open
    datetime_range_2.save()
    payload = client.get(f"/tables/{tabela_bairros.id}/columns/").json()
    assert payload[0]["temporal_coverage"] == {"start": "2022-06", "end": "2024-06"}


@pytest.mark.django_db
def test_a_column_without_coverage_inherits_the_tables(
    client: Client,
    tabela_bairros,
    coluna_nome_bairros,
    coverage_tabela_open,
    datetime_range_1,
):
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    payload = client.get(f"/tables/{tabela_bairros.id}/columns/").json()
    assert payload[0]["temporal_coverage"] == {"start": "2021-06", "end": "2023-06"}


@pytest.mark.django_db
def test_a_directory_column_carries_its_target(
    client: Client,
    tabela_bairros,
    coluna_state_id_bairros,
    tabela_diretorios_brasil_uf,
):
    CloudTable.objects.create(
        table=tabela_diretorios_brasil_uf,
        gcp_project_id="basedosdados",
        gcp_dataset_id="br_bd_diretorios_brasil",
        gcp_table_id="uf",
    )
    payload = client.get(f"/tables/{tabela_bairros.id}/columns/").json()
    dpk = payload[0]["directory_primary_key"]
    assert dpk["name"] == "ID do estado no diretório"
    assert dpk["table"]["cloud_table"]["gcp_table_id"] == "uf"


@pytest.mark.django_db
def test_a_directory_column_without_a_cloud_table_reports_none(
    client: Client, tabela_bairros, coluna_state_id_bairros
):
    payload = client.get(f"/tables/{tabela_bairros.id}/columns/").json()
    assert payload[0]["directory_primary_key"]["table"]["cloud_table"] is None


@pytest.mark.django_db
def test_the_unfiltered_listing_serialises_columns(client: Client, coluna_nome_bairros):
    response = client.get("/columns/")
    assert response.status_code == 200
    assert len(json.loads(response.content)) >= 1


# ---------------------------------------------------------------------------
# DatasetRedirectView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_dataset_slug_redirects_to_the_frontend(client: Client, dataset_dados_mestres):
    response = client.get("/dataset/", {"dataset": "dados_mestres"}, HTTP_HOST=HOST)
    assert response.status_code == 302
    assert response.url == f"http://localhost:3000/dataset/{dataset_dados_mestres.id}"


@pytest.mark.django_db
def test_dashes_in_the_legacy_slug_are_translated_to_underscores(
    client: Client, dataset_dados_mestres
):
    response = client.get("/dataset/", {"dataset": "dados-mestres"}, HTTP_HOST=HOST)
    assert response.url == f"http://localhost:3000/dataset/{dataset_dados_mestres.id}"


@pytest.mark.django_db
def test_a_bigquery_dataset_id_resolves_through_its_cloud_table(
    client: Client, tabela_bairros, dataset_dados_mestres
):
    CloudTable.objects.create(
        table=tabela_bairros,
        gcp_project_id="basedosdados",
        gcp_dataset_id="mundo_transferwise",
        gcp_table_id="taxa_cambio",
    )
    response = client.get("/dataset/", {"dataset": "mundo_transferwise"}, HTTP_HOST=HOST)
    assert response.url == f"http://localhost:3000/dataset/{dataset_dados_mestres.id}"


@pytest.mark.django_db
def test_an_unknown_dataset_redirects_to_404(client: Client):
    response = client.get("/dataset/", {"dataset": "nao_existe"}, HTTP_HOST=HOST)
    assert response.url == "http://localhost:3000/404"


@pytest.mark.django_db
def test_no_dataset_parameter_redirects_to_404(client: Client):
    response = client.get("/dataset/", HTTP_HOST=HOST)
    assert response.url == "http://localhost:3000/404"


@pytest.mark.django_db
def test_an_unmapped_host_raises(client: Client):
    """URL_MAPPING is indexed directly, so an unlisted host is a KeyError.

    Recorded rather than endorsed: the view has no fallback, and any host
    outside the four it knows about produces a 500 instead of a redirect.
    """
    with pytest.raises(KeyError):
        client.get("/dataset/", {"dataset": "x"}, HTTP_HOST="unmapped.example.com")


@pytest.mark.django_db
def test_the_api_root_redirects_to_graphql(client: Client):
    assert client.get("/api/").status_code == 302
    assert client.get("/api/v1/").status_code == 302
