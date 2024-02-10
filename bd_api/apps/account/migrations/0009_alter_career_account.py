# -*- coding: utf-8 -*-
# Generated by Django 4.2.4 on 2023-09-13 23:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0008_alter_account_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="career",
            name="account",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="careers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
