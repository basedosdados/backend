# -*- coding: utf-8 -*-
# Generated by Django 4.2.1 on 2023-06-23 21:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0019_column_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="table",
            name="order",
            field=models.PositiveIntegerField(
                db_index=True, default=0, editable=False, verbose_name="order"
            ),
            preserve_default=False,
        ),
    ]
