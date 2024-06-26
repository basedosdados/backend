# -*- coding: utf-8 -*-
# Generated by Django 4.2.10 on 2024-02-14 15:01

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Metadata",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("key", models.JSONField(default=dict)),
                ("value", models.JSONField(default=dict)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]