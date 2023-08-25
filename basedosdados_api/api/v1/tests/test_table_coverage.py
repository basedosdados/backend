# -*- coding: utf-8 -*-
"""
Pytest Django models tests.
"""

import pytest
from django.core.exceptions import ValidationError

from basedosdados_api.api.v1.models import Table


@pytest.mark.django_db
def test_table_coverage_with_no_date_time_range(
    tabela_bairros,
    coverage_tabela_open,
):
    """
    Test for validating a coverage with no datetime_range.
    """
    coverage_tabela_open.save()

    tabela_bairros.clean()
    tabela_bairros.save()

    assert Table.objects.exists()


@pytest.mark.django_db
def test_table_create_with_overlapping_coverage(
    tabela_pro,
    coverage_tabela_open,
    coverage_tabela_closed,
    datetime_range_1,
    datetime_range_2,
):
    """
    Test for Table with Coverage containing overlapping DateTimeRange.
    Overlapping DateTimeRange in the same Coverage area ust raise ValidationError.
    """
    tabela_pro.save()
    coverage_tabela_open.save()
    datetime_range_1.coverage = coverage_tabela_open
    datetime_range_1.save()

    datetime_range_2.coverage = coverage_tabela_closed
    datetime_range_2.save()
    with pytest.raises(ValidationError):
        tabela_pro.coverages.add(coverage_tabela_open, coverage_tabela_closed)
        tabela_pro.clean()
