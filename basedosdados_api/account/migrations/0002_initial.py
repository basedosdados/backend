# -*- coding: utf-8 -*-
# Generated by Django 4.1.7 on 2023-03-28 16:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("v1", "0001_initial"),
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bdgrouprole",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="group_roles",
                related_query_name="group_role",
                to="v1.organization",
            ),
        ),
        migrations.AddField(
            model_name="bdgrouprole",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="account.bdrole"
            ),
        ),
        migrations.AddField(
            model_name="bdgroup",
            name="roles",
            field=models.ManyToManyField(
                blank=True,
                related_name="groups",
                related_query_name="group",
                through="account.BDGroupRole",
                to="account.bdrole",
                verbose_name="Roles",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                related_name="users",
                related_query_name="user",
                to="account.bdgroup",
                verbose_name="Grupos",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="organizations",
            field=models.ManyToManyField(
                blank=True,
                related_name="users",
                related_query_name="user",
                to="v1.organization",
                verbose_name="Organizações",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.permission",
                verbose_name="user permissions",
            ),
        ),
        migrations.AddConstraint(
            model_name="bdgrouprole",
            constraint=models.UniqueConstraint(
                fields=("group", "role", "organization"),
                name="unique_group_role_organization",
            ),
        ),
    ]
