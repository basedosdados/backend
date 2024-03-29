# -*- coding: utf-8 -*-
# Generated by Django 4.2.6 on 2023-11-27 18:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("djstripe", "0012_2_8"),
        ("account", "0011_subscription"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="subscription",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="internal_subscription",
                to="djstripe.subscription",
            ),
        ),
    ]
