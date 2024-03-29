# -*- coding: utf-8 -*-
# Generated by Django 4.2.6 on 2024-02-04 16:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0026_alter_table_source_bucket_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="page_views",
            field=models.BigIntegerField(
                default=0, help_text="Number of page views by Google Analytics"
            ),
        ),
        migrations.AddField(
            model_name="table",
            name="page_views",
            field=models.BigIntegerField(
                default=0, help_text="Number of page views by Google Analytics"
            ),
        ),
    ]
