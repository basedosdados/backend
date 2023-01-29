# -*- coding: utf-8 -*-
# Generated by Django 4.1.3 on 2022-12-16 13:34

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BigQueryTypes",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
            ],
            options={
                "verbose_name": "BigQuery Type",
                "verbose_name_plural": "BigQuery Types",
                "db_table": "bigquery_types",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Dataset",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(unique=True)),
                ("name_en", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255)),
            ],
            options={
                "verbose_name": "Dataset",
                "verbose_name_plural": "Datasets",
                "db_table": "dataset",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(unique=True)),
                ("name_en", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255)),
                ("website", models.URLField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "db_table": "organization",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Table",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(unique=True)),
                ("name_en", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "is_directory",
                    models.BooleanField(blank=True, default=False, null=True),
                ),
                ("data_cleaned_description", models.TextField(blank=True, null=True)),
                ("data_cleaned_code_url", models.URLField(blank=True, null=True)),
                ("raw_data_url", models.URLField(blank=True, null=True)),
                ("auxiliary_files_url", models.URLField(blank=True, null=True)),
                ("architecture_url", models.URLField(blank=True, null=True)),
                (
                    "source_bucket_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "uncompressed_file_size",
                    models.BigIntegerField(blank=True, null=True),
                ),
                ("compressed_file_size", models.BigIntegerField(blank=True, null=True)),
                ("number_of_rows", models.BigIntegerField(blank=True, null=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tables",
                        to="v1.dataset",
                    ),
                ),
            ],
            options={
                "verbose_name": "Table",
                "verbose_name_plural": "Tables",
                "db_table": "table",
                "ordering": ["slug"],
            },
        ),
        migrations.AddField(
            model_name="dataset",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="datasets",
                to="v1.organization",
            ),
        ),
        migrations.CreateModel(
            name="Column",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name_en", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255)),
                ("is_in_staging", models.BooleanField(default=True)),
                ("is_partition", models.BooleanField(default=False)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "coverage_by_dictionary",
                    models.BooleanField(blank=True, default=False, null=True),
                ),
                (
                    "measurement_unit",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "has_sensitive_data",
                    models.BooleanField(blank=True, default=False, null=True),
                ),
                ("observations", models.TextField(blank=True, null=True)),
                (
                    "bigquery_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="columns",
                        to="v1.bigquerytypes",
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="columns",
                        to="v1.table",
                    ),
                ),
            ],
            options={
                "verbose_name": "Column",
                "verbose_name_plural": "Columns",
                "db_table": "column",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="CloudTable",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("gcp_project_id", models.CharField(max_length=255)),
                ("gcp_dataset_id", models.CharField(max_length=255)),
                ("gcp_table_id", models.CharField(max_length=255)),
                (
                    "columns",
                    models.ManyToManyField(related_name="cloud_tables", to="v1.column"),
                ),
                (
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cloud_tables",
                        to="v1.table",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cloud Table",
                "verbose_name_plural": "Cloud Tables",
                "db_table": "cloud_table",
                "ordering": ["id"],
            },
        ),
    ]