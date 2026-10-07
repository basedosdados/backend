# -*- coding: utf-8 -*-
"""
Tests for researchers, invited researcher terms, journals and research papers.
"""

from datetime import date, timedelta
from json import loads

import pytest
from django.core.exceptions import ValidationError
from graphene_django.utils.testing import graphql_query

from backend.apps.api.v1.models import (
    InvitedResearcherTerm,
    Journal,
    Researcher,
    ResearchPaper,
    add_years,
)

GRAPHQL_URL = "/api/v1/graphql"


@pytest.fixture(name="researcher")
def fixture_researcher(db, tema_educacao):
    researcher = Researcher.objects.create(
        slug="maria-silva",
        name="Maria Silva",
        affiliation="Universidade de São Paulo",
        description_pt="Pesquisadora em economia da educação.",
        description_en="Researcher in the economics of education.",
        description_es="Investigadora en economía de la educación.",
    )
    researcher.themes.add(tema_educacao)
    return researcher


def test_add_years_handles_leap_day():
    assert add_years(date(2026, 3, 1), 2) == date(2028, 3, 1)
    assert add_years(date(2028, 2, 29), 2) == date(2030, 2, 28)


@pytest.mark.django_db
def test_term_end_defaults_to_two_years(researcher):
    term = InvitedResearcherTerm.objects.create(researcher=researcher, start_at=date(2026, 3, 1))
    assert term.end_at == date(2028, 3, 1)


@pytest.mark.django_db
def test_term_end_before_start_is_invalid(researcher):
    term = InvitedResearcherTerm(
        researcher=researcher, start_at=date(2026, 3, 1), end_at=date(2026, 1, 1)
    )
    with pytest.raises(ValidationError):
        term.full_clean()


@pytest.mark.django_db
def test_is_invited_researcher(researcher):
    today = date.today()
    assert not researcher.is_invited_researcher

    InvitedResearcherTerm.objects.create(
        researcher=researcher,
        start_at=today - timedelta(days=900),
        end_at=today - timedelta(days=1),
    )
    assert not researcher.is_invited_researcher

    InvitedResearcherTerm.objects.create(researcher=researcher, start_at=today)
    assert researcher.is_invited_researcher


@pytest.mark.django_db
def test_research_paper_doi_is_normalized(researcher):
    journal = Journal.objects.create(slug="aer", name="American Economic Review")
    paper = ResearchPaper(
        title="A paper",
        authors="Silva, M. and Souza, J.",
        journal=journal,
        year=2025,
        doi="https://doi.org/10.1257/aer.20190001",
    )
    paper.full_clean()
    paper.save()
    paper.researchers.add(researcher)

    assert paper.doi == "10.1257/aer.20190001"
    assert paper.doi_url == "https://doi.org/10.1257/aer.20190001"
    assert list(researcher.research_papers.all()) == [paper]


@pytest.mark.django_db
def test_researchers_are_public_in_graphql(client, researcher):
    InvitedResearcherTerm.objects.create(researcher=researcher, cohort=1, start_at=date.today())
    query = """
        query {
          allResearcher {
            edges {
              node {
                name
                descriptionEn
                isInvitedResearcher
                themes { edges { node { slug } } }
                invitedResearcherTerms { edges { node { cohort startAt endAt } } }
              }
            }
          }
        }
    """
    response = graphql_query(query=query, client=client, graphql_url=GRAPHQL_URL)
    result = loads(response.content)

    assert "errors" not in result
    node = result["data"]["allResearcher"]["edges"][0]["node"]
    assert node["name"] == "Maria Silva"
    assert node["descriptionEn"] == "Researcher in the economics of education."
    assert node["isInvitedResearcher"] is True
    assert node["themes"]["edges"][0]["node"]["slug"] == "educacao"
    assert node["invitedResearcherTerms"]["edges"][0]["node"]["cohort"] == 1
