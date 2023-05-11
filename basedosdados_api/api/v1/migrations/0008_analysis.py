# -*- coding: utf-8 -*-
# Generated by Django 4.2.1 on 2023-05-06 18:26

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0007_alter_entitycategory_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Analysis",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "analysis_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses",
                        to="v1.analysistype",
                    ),
                ),
            ],
            options={
                "verbose_name": "Analysis",
                "verbose_name_plural": "Analyses",
                "db_table": "analysis",
                "ordering": ["id"],
            },
        ),
    ]