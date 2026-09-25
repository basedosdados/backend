# -*- coding: utf-8 -*-
"""
Pytest Django models tests.
"""

import pytest


@pytest.mark.django_db
def test_column_coverage_with_empty_date_time_range(
    tabela_bairros,
    coluna_nome_bairros,
    coverage_tabela_open,
    datetime_range_1,
    coverage_coluna_open,
    datetime_range_empty,
):
    """
    Test for inheritance of column coverage. The table has a datetime_range coverage,
    but the data in column datetime_range is empty.
    In this case, the column coverage should be the same as the table coverage.
    """
    # creates a coverage for the table, create a datetime_range for the table
    # and add the datetime_range to the coverage
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    coverage_tabela_open.datetime_ranges.add(datetime_range_1)

    # creates a coverage for the column and add an empty datetime_range to the coverage
    datetime_range_empty.coverage = coverage_coluna_open
    datetime_range_empty.save()

    assert tabela_bairros.temporal_coverage == {"start": "2021-06", "end": "2023-06"}
    assert coluna_nome_bairros.temporal_coverage == {"start": "2021-06", "end": "2023-06"}


@pytest.mark.django_db
def test_column_coverage_with_no_date_time_range(
    tabela_bairros, coluna_nome_bairros, coverage_tabela_open, datetime_range_1
):
    """
    Test for inheritance of column coverage. The table has a datetime_range coverage,
    but the data in column datetime_range is not set.
    In this case, the column coverage should be the same as the table coverage.
    """
    # creates a coverage for the table, add a datetime_range for the table
    # but no datetime_range is added to the column coverage
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    coverage_tabela_open.datetime_ranges.add(datetime_range_1)

    assert tabela_bairros.temporal_coverage == {"start": "2021-06", "end": "2023-06"}
    assert coluna_nome_bairros.temporal_coverage == {"start": "2021-06", "end": "2023-06"}


@pytest.mark.django_db
def test_column_coverage_with_date_time_range(
    tabela_bairros,
    coluna_nome_bairros,
    coverage_tabela_open,
    coverage_coluna_open,
    datetime_range_1,
    datetime_range_2,
):
    """
    Test for inheritance of column coverage. The table has a datetime_range coverage,
    and the data in column datetime_range is set.
    In this case, temporal_coverage must return the column coverage.
    """
    # creates a coverage for the table, add a datetime_range for the table
    # and add the datetime_range to the column coverage
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    coverage_tabela_open.datetime_ranges.add(datetime_range_1)

    datetime_range_2.coverage = coverage_coluna_open
    datetime_range_2.save()
    coverage_coluna_open.datetime_ranges.add(datetime_range_2)

    assert tabela_bairros.temporal_coverage == {"start": "2021-06", "end": "2023-06"}
    assert coluna_nome_bairros.temporal_coverage == {"start": "2022-06", "end": "2024-06"}
