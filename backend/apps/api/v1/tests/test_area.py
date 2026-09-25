# -*- coding: utf-8 -*-
"""Tests for Area.clean().

Area encodes the spatial hierarchy every coverage rolls up through, and its
validation is the only thing keeping that hierarchy consistent.
"""

import pytest
from django.core.exceptions import ValidationError

from backend.apps.api.v1.models import Area, Entity, EntityCategory


@pytest.fixture(name="entity_spatial")
def fixture_entity_spatial():
    category = EntityCategory.objects.create(slug="spatial", name="Spatial")
    return Entity.objects.create(slug="municipality", name="Município", category=category)


@pytest.mark.django_db
def test_area_without_parent_is_valid():
    area = Area(slug="br", name="Brasil", administrative_level=0)
    area.clean()


@pytest.mark.django_db
@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_accepted_administrative_levels(level):
    Area(slug=f"lvl{level}", name="Area", administrative_level=level).clean()


@pytest.mark.django_db
@pytest.mark.parametrize("level", [4, 5, -1])
def test_rejected_administrative_levels(level):
    """The field offers 0-5 as choices but clean() only accepts 0-3."""
    area = Area(slug="area", name="Area", administrative_level=level)
    with pytest.raises(ValidationError) as exc:
        area.clean()
    assert "administrative_level" in exc.value.message_dict


@pytest.mark.django_db
def test_entity_must_be_spatial(entity_anual):
    """entity_anual belongs to the "time" category."""
    area = Area(slug="br", name="Brasil", administrative_level=0, entity=entity_anual)
    with pytest.raises(ValidationError) as exc:
        area.clean()
    assert "entity" in exc.value.message_dict


@pytest.mark.django_db
def test_spatial_entity_is_accepted(entity_spatial):
    Area(slug="br", name="Brasil", administrative_level=0, entity=entity_spatial).clean()


@pytest.mark.django_db
def test_parent_requires_an_administrative_level():
    parent = Area.objects.create(slug="br", name="Brasil", administrative_level=0)
    area = Area(slug="br_mg", name="Minas Gerais", parent=parent)
    with pytest.raises(ValidationError) as exc:
        area.clean()
    assert "administrative_level" in exc.value.message_dict


@pytest.mark.django_db
def test_parent_must_have_an_administrative_level():
    parent = Area.objects.create(slug="br", name="Brasil")
    area = Area(slug="br_mg", name="Minas Gerais", administrative_level=1, parent=parent)
    with pytest.raises(ValidationError) as exc:
        area.clean()
    assert "parent" in exc.value.message_dict


@pytest.mark.django_db
def test_parent_must_be_exactly_one_level_above():
    parent = Area.objects.create(slug="br", name="Brasil", administrative_level=0)
    area = Area(slug="br_mg_3100104", name="Belo Horizonte", administrative_level=2, parent=parent)
    with pytest.raises(ValidationError) as exc:
        area.clean()
    assert "parent" in exc.value.message_dict


@pytest.mark.django_db
def test_valid_parent_child_pair():
    parent = Area.objects.create(slug="br", name="Brasil", administrative_level=0)
    Area(slug="br_mg", name="Minas Gerais", administrative_level=1, parent=parent).clean()


@pytest.mark.django_db
def test_world_parent_skips_the_level_check():
    """ "world" is the hierarchy root and is exempt from the level relationship."""
    world = Area.objects.create(slug="world", name="Mundo")
    Area(slug="br", name="Brasil", administrative_level=0, parent=world).clean()


@pytest.mark.django_db
def test_str_includes_name_and_slug():
    area = Area(slug="br_mg", name="Minas Gerais")
    assert str(area) == "Minas Gerais (br_mg)"
