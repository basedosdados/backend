# -*- coding: utf-8 -*-
import json
import os
from os import getenv

import requests
from django.core.management.base import BaseCommand
from tqdm import tqdm

BASE_URL = "https://perguntas.basedosdados.org"
METABASE_USER = getenv("METABASE_USER")
METABASE_PASSWORD = getenv("METABASE_PASSWORD")


class Table:
    def __init__(self, id, name, fields):
        self.id = id
        self.name = name
        self.fields = fields

    def __str__(self):
        return self.name


class Command(BaseCommand):
    help = "Fetch data from Metabase"

    def authenticate(self) -> str:
        headers = {
            "Content-Type": "application/json",
        }

        json_data = {
            "username": METABASE_USER,
            "password": METABASE_PASSWORD,
        }

        response = requests.post(BASE_URL + "/api/session", headers=headers, json=json_data).json()

        if "id" not in response:
            self.stderr.write("Falha na autenticação.")
            return ""

        return response["id"]

    def get_headers(self, token: str):
        return {
            "Content-Type": "application/json",
            "X-Metabase-Session": token,
        }

    def get_databases(self, token: str):
        headers = self.get_headers(token)

        response = requests.get(BASE_URL + "/api/database", headers=headers)

        return response.json()["data"]

    def get_tables(self, token: str, database_id: int):
        headers = self.get_headers(token)

        response = requests.get(BASE_URL + f"/api/database/{database_id}/metadata", headers=headers)

        json_data = response.json()
        tables = []

        for table in json_data["tables"]:
            if table["name"].startswith("account"):
                continue

            fields = [field["name"] for field in table["fields"]]
            tables.append(Table(table["id"], table["name"], fields))

        return tables

    def get_table_data(self, token: str, database_id: int, table: Table):
        headers = self.get_headers(token)
        fields = [f'"{field}"' for field in table.fields]
        formated_field = ", ".join(fields)
        query = f'SELECT {formated_field} FROM "{table.name}"'

        payload = {
            "database": database_id,
            "native": {
                "query": query,
            },
            "type": "native",
        }

        response = requests.post(BASE_URL + "/api/dataset", headers=headers, json=payload)

        if response.status_code != 202:
            return

        response_json = response.json()
        rows = []

        for row in response_json["data"]["rows"]:
            instance = {}
            for i, field in enumerate(table.fields):
                instance[field] = row[i]

            rows.append(instance)

        if len(rows) > 0:
            self.save_data(table.name, json.dumps(rows, ensure_ascii=False, indent=4))
        else:
            self.stdout.write(self.style.WARNING(f"No data found for {str(table)}"))
            self.stdout.write(self.style.WARNING(query))

    def clean_data(self):
        directory = os.path.join(os.getcwd(), "metabase_data")

        if os.path.exists(directory) and os.path.isdir(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                os.remove(file_path)

    def save_data(self, table_name, data):
        directory = os.path.join(os.getcwd(), "metabase_data")

        if not os.path.exists(directory):
            os.makedirs(directory)

        file_path = os.path.join(directory, f"{table_name}.json")

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(data)

    def handle(self, *args, **kwargs):
        token = self.authenticate()

        databases = self.get_databases(token)

        database = next(
            (db for db in databases if db["name"] == "Metadados"),
            None,
        )

        self.clean_data()
        tables = self.get_tables(token, database["id"])

        for table in tqdm(tables, desc="Fetching tables"):
            self.stdout.write(f"Fetching data from {str(table)}")
            self.get_table_data(token, database["id"], table)

        self.stdout.write(self.style.SUCCESS("Data fetched successfully."))
