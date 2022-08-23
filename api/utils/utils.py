# -*- coding: utf-8 -*-
"""
General utilities for all paths
"""

from os import getenv
from google.oauth2 import service_account
from google.cloud import storage

import pandas_gbq
import hvac


def get_vault_client() -> hvac.Client:
    """
    Get the vault client

    Environment Variables:
        VAULT_ADDR (str) : the address of the vault
        VAULT_TOKEN (str): the token to be used to access the vault

    Returns:
        hvac.Client: the vault client
    """
    return hvac.Client(
        url=getenv('VAULT_ADDRESS'),
        token=getenv('VAULT_TOKEN')
    )


def get_vault_secret(secret_path: str, client: hvac.Client = None) -> dict:
    """
    Get the secret from Vault.

    Args:
        secret_path (str) : the path of the secret
        client (hvac.Client) : the client to be used to access the vault

    Returns:
        dict: the secret
    """
    vault_client = client if client else get_vault_client()
    return vault_client.secrets.kv.read_secret_version(secret_path)['data']


def zip_and_save_bq_table(dataset: str, table:str, limit: int = 20000) -> str:
    """
    Compress a table from BigQuery Dataset to zip file, and upload it to the bucket.
    The file will be uploaded to the <BUCKET_NAME>/datasets/<dataset>/<table>.csv.zip

    Args:
        secret_path (str)     : the path of the Google Service Account secret
        dataset (str)         : the name of the dataset to be used for the pandas_gbq
        table (str)           : the name of the table to be used for the pandas_gbq
        limit (int, optional) : rows limit for the pandas_gbq. Defaults to 20000.

    Returns:
        str: the URI of the uploaded file
    """
    secret_path = 'terraform_credentials/basedosdados-dev'
    credentials = get_vault_secret(secret_path)['data']['GCP_SA']
    project_id = credentials['project_id']
    pandas_gbq.context.credentials = service_account.Credentials.from_service_account_info(credentials)
    pandas_gbq.context.project = project_id
    query = f"SELECT * FROM `{project_id}.{dataset}.{table}` LIMIT {limit}"
    df = pandas_gbq.read_gbq(query, project_id)
    df.to_csv(f"{table}.csv.zip", compression="zip", index=False)

    client = storage.Client(
        project=project_id,
        credentials=service_account.Credentials.from_service_account_info(credentials)
    )
    bucket = client.get_bucket(getenv('BUCKET_NAME', 'basedosdados-dev'))
    blob = bucket.blob(f'datasets/{dataset}/{table}.csv.zip')
    blob.upload_from_filename(f'{table}.csv.zip')

    return blob.public_url
