# -*- coding: utf-8 -*-
from typing import Iterable, Optional

from django.db import models

from basedosdados_api.api.v1.utils import check_snake_case


class Organization(models.Model):
    id = models.UUIDField(primary_key=True)

    def __str__(self):
        return self.id

    class Meta:
        db_table = "organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["id"]


class Dataset(models.Model):
    id = models.UUIDField(primary_key=True)
    organization = models.ForeignKey(
        "Organization", on_delete=models.CASCADE, related_name="datasets"
    )

    def __str__(self):
        return self.id

    class Meta:
        db_table = "dataset"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        ordering = ["id"]


class Table(models.Model):
    id = models.UUIDField(primary_key=True)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="tables"
    )

    def __str__(self):
        return self.id

    class Meta:
        db_table = "table"
        verbose_name = "Table"
        verbose_name_plural = "Tables"
        ordering = ["id"]


class Column(models.Model):
    id = models.UUIDField(primary_key=True)
    table = models.ForeignKey("Table", on_delete=models.CASCADE, related_name="columns")

    def __str__(self):
        return self.id

    class Meta:
        db_table = "column"
        verbose_name = "Column"
        verbose_name_plural = "Columns"
        ordering = ["id"]


class CloudTable(models.Model):
    table = models.OneToOneField(
        "Table", on_delete=models.CASCADE, related_name="cloud_table", primary_key=True
    )
    gcp_project_id = models.CharField(max_length=255)
    gcp_dataset_id = models.CharField(max_length=255)
    gcp_table_id = models.CharField(max_length=255)

    def __str__(self):
        return self.id

    def clean(self) -> None:
        if not check_snake_case(self.gcp_project_id):
            raise ValueError("gcp_project_id must be in snake_case.")
        if not check_snake_case(self.gcp_dataset_id):
            raise ValueError("gcp_dataset_id must be in snake_case.")
        if not check_snake_case(self.gcp_table_id):
            raise ValueError("gcp_table_id must be in snake_case.")
        return super().clean()

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None,
    ) -> None:
        self.clean()
        return super().save(force_insert, force_update, using, update_fields)

    class Meta:
        db_table = "cloud_table"
        verbose_name = "Cloud Table"
        verbose_name_plural = "Cloud Tables"
        ordering = ["id"]
