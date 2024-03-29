# -*- coding: utf-8 -*-
# Generated by Django 4.1.7 on 2023-04-27 21:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="column",
            name="is_closed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="dataset",
            name="is_closed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="table",
            name="is_closed",
            field=models.BooleanField(default=False),
        ),
    ]
