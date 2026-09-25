# -*- coding: utf-8 -*-
"""Tests for backend.custom.utils.

check_snake_case and check_kebab_case gate CloudTable validation: they decide
whether a BigQuery project, dataset, and table identifier is well formed.
"""

import pytest

from backend.custom.utils import check_kebab_case, check_snake_case


@pytest.mark.parametrize(
    "name",
    ["tabela_bairros", "bairros", "br_ms_mte_caged", "tabela1", "1tabela", "a", "a_1"],
)
def test_snake_case_accepts(name):
    assert check_snake_case(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "Tabela",  # uppercase
        "TABELA",
        "tabela-bairros",  # kebab separator
        "tabela bairros",  # space
        "tabela.bairros",  # dot
        "_tabela",  # leading underscore
        "tabela__bairros!",  # punctuation
        "tabelá",  # accented
    ],
)
def test_snake_case_rejects(name):
    assert check_snake_case(name) is False


@pytest.mark.parametrize("name", ["basedosdados-dev", "basedosdados", "bd1", "a-b-c"])
def test_kebab_case_accepts(name):
    assert check_kebab_case(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "Basedosdados",
        "base_dos_dados",  # snake separator
        "-basedosdados",  # leading dash
        "base dos dados",
        "base.dos.dados",
    ],
)
def test_kebab_case_rejects(name):
    assert check_kebab_case(name) is False


@pytest.mark.parametrize("check", [check_snake_case, check_kebab_case])
def test_empty_string_raises(check):
    """Both helpers index name[0] without a length guard.

    Documented here so the behaviour is a decision rather than a surprise: callers
    must not pass an empty string. CloudTable.clean() guards each call with a
    truthiness check for this reason.
    """
    with pytest.raises(IndexError):
        check("")
