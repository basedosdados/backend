# -*- coding: utf-8 -*-
"""
Pytest Django models tests.
"""
import pytest


@pytest.mark.django_db
def test_column_coverage(
    tabela_bairros,
    coluna_nome_bairros,
    coverage_tabela_open,
    datetime_range_1,
    coverage_coluna_open,
    datetime_range_empty,
):
    """
    Test for inheritance of column coverage. The table has a datetime_range coverage,
    but the data in column datetime_range is not set. In this case, the column coverage
    should be the same as the table coverage.
    """
    # creates a coverage for the table, create a datetime_range for the table
    # and add the datetime_range to the coverage
    coverage_tabela_open.save()
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()
    coverage_tabela_open.datetime_ranges.add(datetime_range_1)

    # creates a coverage for the column and add an empty datetime_range to the coverage
    coverage_coluna_open.save()
    datetime_range_empty.coverage = coverage_coluna_open
    datetime_range_empty.save()

    assert coluna_nome_bairros.coverage == ""
    assert tabela_bairros.coverages.first().datetime_ranges.first().start_year == 2021
    assert (
        coluna_nome_bairros.coverages.first().datetime_ranges.first().start_year is None
    )
