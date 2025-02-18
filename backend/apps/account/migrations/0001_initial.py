# -*- coding: utf-8 -*-
# Generated by Django 4.1.7 on 2023-03-28 16:51

import uuid

import django.db.models.deletion
from django.db import migrations, models

import backend.apps.account.models
import backend.apps.api.v1.validators
import backend.custom.storage


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(blank=True, null=True, verbose_name="last login"),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has "
                        "all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "email",
                    models.EmailField(max_length=254, unique=True, verbose_name="Email"),
                ),
                (
                    "username",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        unique=True,
                        verbose_name="Username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(blank=True, max_length=40, verbose_name="Nome"),
                ),
                (
                    "last_name",
                    models.CharField(blank=True, max_length=40, verbose_name="Sobrenome"),
                ),
                (
                    "birth_date",
                    models.DateField(blank=True, null=True, verbose_name="Data de Nascimento"),
                ),
                (
                    "picture",
                    models.ImageField(
                        blank=True,
                        null=True,
                        storage=backend.custom.storage.OverwriteStorage(),
                        upload_to=backend.custom.storage.upload_to,
                        validators=[backend.custom.storage.validate_image],
                        verbose_name="Imagem",
                    ),
                ),
                (
                    "twitter",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Twitter"
                    ),
                ),
                (
                    "linkedin",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Linkedin"
                    ),
                ),
                (
                    "github",
                    models.CharField(blank=True, max_length=255, null=True, verbose_name="Github"),
                ),
                (
                    "website",
                    models.URLField(blank=True, null=True, verbose_name="Website"),
                ),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Descrição"),
                ),
                (
                    "description_pt",
                    models.TextField(blank=True, null=True, verbose_name="Descrição"),
                ),
                (
                    "description_en",
                    models.TextField(blank=True, null=True, verbose_name="Descrição"),
                ),
                (
                    "description_es",
                    models.TextField(blank=True, null=True, verbose_name="Descrição"),
                ),
                (
                    "is_admin",
                    models.BooleanField(
                        default=False,
                        help_text="Indica se tem acesso à administração",
                        verbose_name="Membro da equipe",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Indica se o usuário está ativo",
                        verbose_name="Ativo",
                    ),
                ),
                (
                    "profile",
                    models.IntegerField(
                        choices=[(1, "Staff"), (2, "Visitante"), (3, "Colaborador")],
                        default=2,
                        verbose_name="Perfil",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "account",
                "verbose_name_plural": "accounts",
                "db_table": "account",
                "ordering": ["first_name", "last_name"],
            },
        ),
        migrations.CreateModel(
            name="BDGroup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "BD group",
                "verbose_name_plural": "BD groups",
            },
            managers=[
                ("objects", backend.apps.account.models.BDGroupManager()),
            ],
        ),
        migrations.CreateModel(
            name="RegistrationToken",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "token",
                    models.CharField(default=uuid.uuid4, max_length=255, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("used_at", models.DateTimeField(auto_now=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Registration Token",
                "verbose_name_plural": "Registration Tokens",
            },
        ),
        migrations.CreateModel(
            name="BDRole",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "permissions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="roles",
                        related_query_name="role",
                        to="auth.permission",
                        verbose_name="Permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "BD role",
                "verbose_name_plural": "BD roles",
            },
            managers=[
                ("objects", backend.apps.account.models.BDRoleManager()),
            ],
        ),
        migrations.CreateModel(
            name="BDGroupRole",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="account.bdgroup",
                    ),
                ),
            ],
            options={
                "verbose_name": "BD group role",
                "verbose_name_plural": "BD group roles",
            },
        ),
    ]
