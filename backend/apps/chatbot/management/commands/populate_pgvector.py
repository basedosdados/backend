# -*- coding: utf-8 -*-
import json
import os
from itertools import islice
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection as django_connection
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_postgres import PGVector
from loguru import logger

from backend.apps.chatbot.context_provider import PostgresContextProvider
from backend.apps.chatbot.context_provider.metadata_formatter import DatasetMetadata


def batched(iterable, batch_size: int):
    if batch_size < 1:
        raise ValueError("batch_size must be at least one")

    iterator = iter(iterable)

    while batch := tuple(islice(iterator, batch_size)):
        yield batch


class Command(BaseCommand):
    name = Path(__file__).stem
    help = "Populates the PGVector collection with embeddings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size", type=int, default=1000, help="Number of documents to embed per batch"
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]

        logger.info(f"[{self.name}]: Using batch size {batch_size}")

        db_host = os.environ["DB_HOST"]
        db_port = os.environ["DB_PORT"]
        db_name = os.environ["DB_NAME"]
        db_user = os.environ["DB_USER"]
        db_password = os.environ["DB_PASSWORD"]

        bq_billing_project = os.environ["BILLING_PROJECT_ID"]
        bq_query_project = os.environ["QUERY_PROJECT_ID"]

        embedding_model = os.getenv("EMBEDDING_MODEL")
        pgvector_collection = os.getenv("PGVECTOR_COLLECTION")

        if embedding_model is None or pgvector_collection is None:
            self.stdout.write(self.style.NOTICE(f"> Skipping {self.name}..."))
            return

        embeddings = VertexAIEmbeddings(embedding_model)

        connection = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        vector_store = PGVector(
            embeddings=embeddings,
            connection=connection,
            collection_name=pgvector_collection,
            use_jsonb=True,
        )

        context_provider = PostgresContextProvider(
            billing_project=bq_billing_project,
            query_project=bq_query_project,
            metadata_vector_store=None,
        )

        # storing existing dataset ids for skipping them during embeddings creation
        with django_connection.cursor() as cursor:
            cursor.execute(
                "SELECT cmetadata FROM langchain_pg_embedding "
                "WHERE collection_id = ("
                "   SELECT uuid from langchain_pg_collection WHERE name = %s"
                ")",
                (pgvector_collection,),
            )
            metadata = [json.loads(metadata[0]) for metadata in cursor.fetchall()]
            datasets = [DatasetMetadata(**m) for m in metadata]
            datasets_ids = {dataset.id for dataset in datasets}

        logger.info(f"[{self.name}]: Formatting metadata...")

        texts = []
        texts_metadata = []

        for dataset_metadata in context_provider._get_metadata():
            # skipping existing dataset ids
            if dataset_metadata.id in datasets_ids:
                continue

            text = (
                f"Dataset: {dataset_metadata.name}\n\n"
                f"Description: {dataset_metadata.description}\n\n"
                "Tables:"
            )

            for table in dataset_metadata.tables:
                text += f"\n- {table.name}: {table.description}"

            texts.append(text)

            texts_metadata.append(dataset_metadata.model_dump())

        n_documents = len(texts)

        logger.info(f"[{self.name}]: Found {n_documents} new documents")

        if n_documents == 0:
            logger.info(f"[{self.name}]: All documents already embedded. Skipping...")
            return

        logger.info(f"[{self.name}]: Creating embeddings...")

        count = 0

        for batch in batched(zip(texts, texts_metadata), batch_size):
            text_batch, metadata_batch = zip(*batch)

            _ = vector_store.add_texts(
                texts=text_batch,
                metadatas=metadata_batch,
            )

            count += len(text_batch)
            logger.info(f"[{self.name}]: Embedded {count}/{len(texts)} documents")

        logger.success(f"[{self.name}]: Embeddings created successfully")
