# -*- coding: utf-8 -*-
# Generated by Django 4.2.1 on 2023-07-21 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0021_informationrequest_order_rawdatasource_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="coverage",
            name="is_closed",
            field=models.BooleanField(default=False, verbose_name="Is Closed"),
        ),
        migrations.AlterField(
            model_name="column",
            name="is_closed",
            field=models.BooleanField(
                default=False, help_text="Column is for BD Pro subscribers only"
            ),
        ),
        migrations.AlterField(
            model_name="dataset",
            name="is_closed",
            field=models.BooleanField(
                default=False, help_text="Dataset is for BD Pro subscribers only"
            ),
        ),
        migrations.AlterField(
            model_name="table",
            name="is_closed",
            field=models.BooleanField(
                default=False, help_text="Table is for BD Pro subscribers only"
            ),
        ),
    ]