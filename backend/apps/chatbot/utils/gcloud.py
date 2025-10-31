# -*- coding: utf-8 -*-
import os
from functools import cache

from google.cloud import bigquery as bq
from google.oauth2.service_account import Credentials


@cache
def get_chatbot_credentials() -> Credentials:
    """Return cached Google Cloud service account credentials."""
    sa_file = os.getenv("CHATBOT_CREDENTIALS")

    if not sa_file:
        raise ValueError(
            "CHATBOT_CREDENTIALS environment variable must be set. "
            "Please provide the path to your service account JSON file."
        )

    if not os.path.exists(sa_file):
        raise FileNotFoundError(f"Service account file not found: {sa_file}")

    return Credentials.from_service_account_file(sa_file)


@cache
def get_bigquery_client() -> bq.Client:
    """Return a cached BigQuery client.

    The client is initialized once using the project ID from the
    `QUERY_PROJECT_ID` environment variable and reused on subsequent calls.

    Returns:
        bigquery.Client: A cached, authenticated BigQuery client.
    """
    # TODO: revert to os.getenv("QUERY_PROJECT_ID")
    project = "basedosdados"

    if not project:
        raise ValueError(
            "QUERY_PROJECT_ID environment variable must be set. "
            "Please provide the ID of your BigQuery project."
        )

    return bq.Client(
        project=project,
        credentials=get_chatbot_credentials(),
    )
