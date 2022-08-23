# -*- coding: utf-8 -*-
"""
Paths for the basedosdados fastapi serverless
"""
from fastapi import FastAPI
from .utils.utils import zip_and_save_bq_table

app = FastAPI()


@app.get('/')
def index():
    """
    """
    return {'data': 'Hello World!'}


@app.get('/zip_table/{dataset}/{table}')
def zip_and_save(dataset: str, table: str, limit: int = 20000) -> str:
    """
    """
    try:
        return zip_and_save_bq_table(dataset, table, limit)
    except Exception as e:
        return str(e)
