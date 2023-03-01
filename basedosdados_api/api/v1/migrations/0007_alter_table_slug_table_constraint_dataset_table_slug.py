# -*- coding: utf-8 -*-
# Generated by Django 4.1.3 on 2023-02-28 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0006_area_key_area_name_area_name_en_area_name_pt"),
    ]

    operations = [
        migrations.AlterField(
            model_name="table",
            name="slug",
            field=models.SlugField(),
        ),
        migrations.AddConstraint(
            model_name="table",
            constraint=models.UniqueConstraint(
                fields=("dataset", "slug"), name="constraint_dataset_table_slug"
            ),
        ),
    ]
