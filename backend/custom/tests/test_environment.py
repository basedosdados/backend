# -*- coding: utf-8 -*-
"""Tests for backend.custom.environment.

These helpers decide whether the deployment is production. Several code paths
branch on them — activation emails are only sent when is_prd() is true, and
production_task/not_production_task gate whole functions — so a wrong answer here
is silent rather than loud.
"""

from importlib import reload

import pytest

from backend.custom import environment


def configure(monkeypatch, settings_module: str, backend_url: str):
    """Reload the module with a given environment.

    SETTINGS and BACKEND_URL are read once at import time, so the module has to be
    reloaded for a change to take effect.
    """
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", settings_module)
    monkeypatch.setenv("BASE_URL_BACKEND", backend_url)
    reload(environment)
    return environment


@pytest.fixture(autouse=True)
def restore_module():
    """Leave the module as the rest of the suite found it."""
    yield
    reload(environment)


LOCAL = ("backend.settings.local", "https://localhost:8080")
DEV = ("backend.settings.remote", "https://development.backend.basedosdados.org")
STG = ("backend.settings.remote", "https://staging.backend.basedosdados.org")
PRD = ("backend.settings.remote", "https://backend.basedosdados.org")


@pytest.mark.parametrize(
    "config,remote,dev,stg,prd",
    [
        (LOCAL, False, False, False, False),
        (DEV, True, True, False, False),
        (STG, True, False, True, False),
        (PRD, True, False, False, True),
    ],
    ids=["local", "development", "staging", "production"],
)
def test_environment_detection(monkeypatch, config, remote, dev, stg, prd):
    env = configure(monkeypatch, *config)
    assert env.is_remote() is remote
    assert env.is_dev() is dev
    assert env.is_stg() is stg
    assert env.is_prd() is prd


def test_remote_settings_with_local_url_is_not_remote(monkeypatch):
    """Both halves of the check must hold: remote settings alone are not enough."""
    env = configure(monkeypatch, "backend.settings.remote", "https://localhost:8080")
    assert env.is_remote() is False
    assert env.is_prd() is False


def test_local_settings_with_production_url_is_not_remote(monkeypatch):
    env = configure(monkeypatch, "backend.settings.local", "https://backend.basedosdados.org")
    assert env.is_remote() is False
    assert env.is_prd() is False


@pytest.mark.parametrize(
    "config,backend_url,frontend_url",
    [
        (LOCAL, "localhost:8080", "localhost:3000"),
        (DEV, "development.backend.basedosdados.org", "development.basedosdados.org"),
        (STG, "staging.backend.basedosdados.org", "staging.basedosdados.org"),
        (PRD, "backend.basedosdados.org", "basedosdados.org"),
    ],
    ids=["local", "development", "staging", "production"],
)
def test_urls_by_environment(monkeypatch, config, backend_url, frontend_url):
    env = configure(monkeypatch, *config)
    assert env.get_backend_url() == backend_url
    assert env.get_frontend_url() == frontend_url


def test_production_task_runs_only_in_production(monkeypatch):
    env = configure(monkeypatch, *PRD)
    calls = []

    @env.production_task
    def task():
        calls.append(1)
        return "ran"

    assert task() == "ran"
    assert calls == [1]


def test_production_task_is_skipped_outside_production(monkeypatch):
    env = configure(monkeypatch, *STG)
    calls = []

    @env.production_task
    def task():
        calls.append(1)
        return "ran"

    assert task() is None
    assert calls == []


def test_not_production_task_is_skipped_in_production(monkeypatch):
    env = configure(monkeypatch, *PRD)
    calls = []

    @env.not_production_task
    def task():
        calls.append(1)

    assert task() is None
    assert calls == []


def test_not_production_task_runs_outside_production(monkeypatch):
    env = configure(monkeypatch, *DEV)
    calls = []

    @env.not_production_task
    def task():
        calls.append(1)
        return "ran"

    assert task() == "ran"
    assert calls == [1]


def test_decorators_preserve_metadata(monkeypatch):
    env = configure(monkeypatch, *PRD)

    @env.production_task
    def documented_task():
        """A docstring worth keeping."""

    assert documented_task.__name__ == "documented_task"
    assert documented_task.__doc__ == "A docstring worth keeping."


@pytest.mark.parametrize(
    "config,expected",
    [
        (LOCAL, {"http://localhost:3000"}),
        (
            DEV,
            {
                "https://development.basedosdados.org",
                "https://development.data-basis.org",
                "https://development.basedelosdatos.org",
            },
        ),
        (
            STG,
            {
                "https://staging.basedosdados.org",
                "https://staging.data-basis.org",
                "https://staging.basedelosdatos.org",
            },
        ),
        (
            PRD,
            {
                "https://basedosdados.org",
                "https://data-basis.org",
                "https://basedelosdatos.org",
            },
        ),
    ],
    ids=["local", "development", "staging", "production"],
)
def test_allowed_frontend_origins_by_environment(monkeypatch, config, expected):
    """The post-login redirect allowlist. A JWT rides in that redirect, so an
    origin leaking onto this list is a token disclosure, not a cosmetic bug."""
    env = configure(monkeypatch, *config)
    assert env.get_allowed_frontend_origins() == expected


def test_production_origins_are_not_allowed_locally(monkeypatch):
    env = configure(monkeypatch, *LOCAL)
    assert "https://basedosdados.org" not in env.get_allowed_frontend_origins()


def test_every_allowed_origin_is_https_when_remote(monkeypatch):
    for config in (DEV, STG, PRD):
        env = configure(monkeypatch, *config)
        assert all(o.startswith("https://") for o in env.get_allowed_frontend_origins())
