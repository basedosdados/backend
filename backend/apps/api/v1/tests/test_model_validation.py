# -*- coding: utf-8 -*-
"""Tests for the model clean() validators.

Coverage, Update, Poll and QualityCheck all enforce the same shape: exactly one
of a set of mutually exclusive foreign keys must be set. The rule is spelled out
separately in each model, so each copy is checked here.

DateTimeRange gets its own section: its since/until properties assemble a
datetime out of seven nullable integer columns, and everything temporal in the
API is built on top of them.
"""

from datetime import datetime

import pytest
from django.core.exceptions import ValidationError

from backend.apps.api.v1.models import (
    Coverage,
    DateTimeRange,
    Poll,
    QualityCheck,
    Update,
)

# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_coverage_accepts_exactly_one_target(tabela_bairros):
    Coverage(table=tabela_bairros).clean()


@pytest.mark.django_db
def test_coverage_rejects_no_target():
    with pytest.raises(ValidationError):
        Coverage().clean()


@pytest.mark.django_db
def test_coverage_rejects_two_targets(tabela_bairros, coluna_nome_bairros):
    with pytest.raises(ValidationError):
        Coverage(table=tabela_bairros, column=coluna_nome_bairros).clean()


@pytest.mark.django_db
def test_coverage_type_reports_the_target(tabela_bairros, coluna_nome_bairros, raw_data_source):
    assert Coverage(table=tabela_bairros).coverage_type() == "table"
    assert Coverage(column=coluna_nome_bairros).coverage_type() == "column"
    assert Coverage(raw_data_source=raw_data_source).coverage_type() == "raw_data_source"
    assert Coverage().coverage_type() == ""


@pytest.mark.django_db
def test_coverage_str_names_the_target(tabela_bairros, area_br):
    coverage = Coverage(table=tabela_bairros, area=area_br)
    assert str(coverage).startswith("Table: ")
    assert str(tabela_bairros) in str(coverage)


@pytest.mark.django_db
def test_coverage_area_similarity(tabela_bairros, area_br):
    """One area name being a prefix of the other counts as a match."""
    from backend.apps.api.v1.models import Area

    brasil = Area.objects.create(slug="br", name="Brasil")
    brasil_mg = Area.objects.create(slug="br_mg", name="Brasil Minas Gerais")
    outro = Area.objects.create(slug="ar", name="Argentina")

    parent = Coverage(table=tabela_bairros, area=brasil)
    child = Coverage(table=tabela_bairros, area=brasil_mg)
    unrelated = Coverage(table=tabela_bairros, area=outro)
    missing = Coverage(table=tabela_bairros)

    assert parent.get_similarity_of_area(child) == 1
    assert child.get_similarity_of_area(parent) == 1
    assert parent.get_similarity_of_area(unrelated) == 0
    assert parent.get_similarity_of_area(missing) == 0
    assert missing.get_similarity_of_area(parent) == 0


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_update_accepts_exactly_one_target(tabela_bairros):
    Update(table=tabela_bairros).clean()


@pytest.mark.django_db
def test_update_rejects_no_target():
    with pytest.raises(ValidationError):
        Update().clean()


@pytest.mark.django_db
def test_update_rejects_two_targets(tabela_bairros, raw_data_source):
    with pytest.raises(ValidationError):
        Update(table=tabela_bairros, raw_data_source=raw_data_source).clean()


@pytest.mark.django_db
def test_update_entity_must_be_datetime(tabela_bairros, entity_escola):
    """entity_escola belongs to the "education" category."""
    with pytest.raises(ValidationError) as exc:
        Update(table=tabela_bairros, entity=entity_escola).clean()
    assert "entity" in exc.value.message_dict


@pytest.mark.django_db
def test_update_accepts_a_datetime_entity(tabela_bairros, entity_anual):
    entity_anual.category.slug = "datetime"
    entity_anual.category.save()
    Update(table=tabela_bairros, entity=entity_anual).clean()


# ---------------------------------------------------------------------------
# Poll
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_poll_accepts_exactly_one_target(raw_data_source):
    Poll(raw_data_source=raw_data_source).clean()


@pytest.mark.django_db
def test_poll_rejects_no_target():
    with pytest.raises(ValidationError):
        Poll().clean()


@pytest.mark.django_db
def test_poll_rejects_two_targets(raw_data_source, pedido_informacao):
    with pytest.raises(ValidationError):
        Poll(raw_data_source=raw_data_source, information_request=pedido_informacao).clean()


@pytest.mark.django_db
def test_poll_entity_must_be_datetime(raw_data_source, entity_escola):
    with pytest.raises(ValidationError) as exc:
        Poll(raw_data_source=raw_data_source, entity=entity_escola).clean()
    assert "entity" in exc.value.message_dict


# ---------------------------------------------------------------------------
# QualityCheck
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_quality_check_accepts_exactly_one_target(tabela_bairros):
    QualityCheck(table=tabela_bairros).clean()


@pytest.mark.django_db
def test_quality_check_rejects_no_target():
    with pytest.raises(ValidationError):
        QualityCheck().clean()


@pytest.mark.django_db
def test_quality_check_rejects_two_targets(tabela_bairros, dataset_dados_mestres):
    with pytest.raises(ValidationError):
        QualityCheck(table=tabela_bairros, dataset=dataset_dados_mestres).clean()


@pytest.mark.django_db
def test_quality_check_ignores_pipeline_when_counting(tabela_bairros, pipeline):
    """pipeline is not one of the mutually exclusive targets."""
    QualityCheck(table=tabela_bairros, pipeline=pipeline).clean()


# ---------------------------------------------------------------------------
# DateTimeRange
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_since_and_until_assemble_full_datetimes():
    dtr = DateTimeRange(
        start_year=2021,
        start_month=6,
        start_day=15,
        start_hour=10,
        start_minute=30,
        start_second=45,
        end_year=2023,
        end_month=1,
        end_day=2,
    )
    assert dtr.since == datetime(2021, 6, 15, 10, 30, 45)
    assert dtr.until == datetime(2023, 1, 2, 0, 0, 0)


@pytest.mark.django_db
def test_missing_parts_default_to_the_start_of_the_period():
    dtr = DateTimeRange(start_year=2021, end_year=2023)
    assert dtr.since == datetime(2021, 1, 1, 0, 0, 0)
    assert dtr.until == datetime(2023, 1, 1, 0, 0, 0)


@pytest.mark.django_db
def test_since_is_none_without_a_start_year():
    assert DateTimeRange(start_month=6).since is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"start_year": 2021, "start_month": 6, "start_day": 15}, "2021-06-15"),
        ({"start_year": 2021, "start_month": 6}, "2021-06"),
        ({"start_year": 2021}, "2021"),
        ({}, ""),
    ],
)
def test_since_str_precision_follows_the_fields_set(kwargs, expected):
    assert DateTimeRange(**kwargs).since_str == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"end_year": 2023, "end_month": 6, "end_day": 15}, "2023-06-15"),
        ({"end_year": 2023, "end_month": 6}, "2023-06"),
        ({"end_year": 2023}, "2023"),
        ({}, ""),
    ],
)
def test_until_str_precision_follows_the_fields_set(kwargs, expected):
    assert DateTimeRange(**kwargs).until_str == expected


@pytest.mark.django_db
@pytest.mark.parametrize("interval,expected", [(1, "1"), (12, "12"), (None, "0"), (0, "0")])
def test_interval_str(interval, expected):
    assert DateTimeRange(interval=interval).interval_str == expected


@pytest.mark.django_db
def test_clean_rejects_a_start_after_the_end():
    dtr = DateTimeRange(start_year=2024, end_year=2020, interval=1)
    with pytest.raises(ValidationError) as exc:
        dtr.clean()
    assert "date_range" in exc.value.message_dict


@pytest.mark.django_db
def test_clean_requires_an_interval_for_a_bounded_range():
    dtr = DateTimeRange(start_year=2020, end_year=2024)
    with pytest.raises(ValidationError) as exc:
        dtr.clean()
    assert "interval" in exc.value.message_dict


@pytest.mark.django_db
def test_clean_accepts_an_open_ended_range_without_an_interval():
    DateTimeRange(start_year=2020).clean()


@pytest.mark.django_db
def test_clean_accepts_a_valid_bounded_range():
    DateTimeRange(start_year=2020, end_year=2024, interval=1).clean()


@pytest.mark.django_db
def test_overlapping_ranges_are_similar():
    first = DateTimeRange(start_year=2020, end_year=2023, interval=1)
    second = DateTimeRange(start_year=2022, end_year=2025, interval=1)
    assert first.get_similarity_of_datetime(second) == 1


@pytest.mark.django_db
def test_similarity_needs_a_start_on_the_left_and_an_end_on_the_right():
    bounded = DateTimeRange(start_year=2020, end_year=2023, interval=1)
    assert DateTimeRange().get_similarity_of_datetime(bounded) == 0
    assert bounded.get_similarity_of_datetime(DateTimeRange(start_year=2020)) == 0
