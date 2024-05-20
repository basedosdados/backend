# -*- coding: utf-8 -*-
from json import loads
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.test.client import Client
from djstripe.models import Customer as DJStripeCustomer
from graphene_django.utils.testing import graphql_query

from backend.apps.account.models import Account

QUERY = (
    Path(__file__)
    .with_name("tests.gql")
    .read_text()
)  # fmt: skip
GRAPHQL_URL = "/api/graphql/"


@pytest.fixture
def account():
    return Account.objects.create(
        is_active=True,
        username="john.doe",
        password="12345678",
        email="john.doe@email.com",
    )


@pytest.fixture
def customer(account):
    return DJStripeCustomer.objects.create(
        subscriber_id=account.id,
    )


@pytest.fixture
def token(client: Client, account):
    response = graphql_query(
        query=QUERY,
        client=client,
        graphql_url=GRAPHQL_URL,
        operation_name="login",
        variables={
            "email": "john.doe@email.com",
            "password": "12345678",
        },
    )
    result = loads(response.content)
    return result["data"]["tokenAuth"]["token"]


@pytest.fixture
def query(client: Client, token):
    def func(operation_name, *args, **kwargs):
        response = graphql_query(
            *args,
            **kwargs,
            query=QUERY,
            client=client,
            graphql_url=GRAPHQL_URL,
            operation_name=operation_name,
            headers={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        return loads(response.content)

    return func


@pytest.mark.django_db
def test_all_stripe_price_call(query):
    response = query("AllStripePrice")
    assert not response["data"]["allStripePrice"]["edges"]


@pytest.mark.django_db
@patch("backend.apps.payment.graphql.StripeCustomer")
@patch("backend.apps.payment.graphql.DJStripeCustomer")
def test_create_stripe_customer_call(
    djst_customer: MagicMock, strp_customer: MagicMock, query, account
):
    query("CreateStripeCustomer")
    djst_customer.create.assert_called_once()
    strp_customer.modify.assert_called_once()


@pytest.mark.django_db
@patch("backend.apps.payment.graphql.StripeCustomer")
def test_update_stripe_customer_call(strp_customer: MagicMock, query, account, customer):
    query("UpdateStripeCustomer")
    strp_customer.modify.assert_called_once()
