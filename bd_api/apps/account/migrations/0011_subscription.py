# -*- coding: utf-8 -*-
# Generated by Django 4.2.6 on 2023-11-12 19:43

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0010_alter_account_is_admin"),
    ]

    operations = [
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                (
                    "is_active",
                    models.BooleanField(
                        default=False,
                        help_text="Indica se a inscrição está ativa",
                        verbose_name="Ativo",
                    ),
                ),
                (
                    "admin",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="admin_subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("subscribers", models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Subscription",
                "verbose_name_plural": "Subscriptions",
            },
        ),
    ]
