# Generated by Django 4.2.18 on 2025-02-04 04:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0018_account_gcp_email"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Name")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Role",
                "verbose_name_plural": "Roles",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Name")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Team",
                "verbose_name_plural": "Teams",
                "ordering": ["name"],
            },
        ),
        migrations.AlterField(
            model_name="career",
            name="end_at",
            field=models.DateField(blank=True, null=True, verbose_name="End at"),
        ),
        migrations.AlterField(
            model_name="career",
            name="level",
            field=models.CharField(blank=True, max_length=40, verbose_name="Level"),
        ),
        migrations.AlterField(
            model_name="career",
            name="role",
            field=models.CharField(blank=True, max_length=40, verbose_name="Role"),
        ),
        migrations.AlterField(
            model_name="career",
            name="start_at",
            field=models.DateField(blank=True, null=True, verbose_name="Start at"),
        ),
        migrations.AddField(
            model_name="career",
            name="team_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="careers",
                to="account.team",
            ),
        ),
    ]
