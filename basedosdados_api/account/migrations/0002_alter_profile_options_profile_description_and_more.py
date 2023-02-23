# Generated by Django 4.1.3 on 2023-02-16 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="profile",
            options={
                "ordering": ["name"],
                "verbose_name": "Profile",
                "verbose_name_plural": "Profiles",
            },
        ),
        migrations.AddField(
            model_name="profile",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="description_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="description_pt",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterModelTable(
            name="profile",
            table="profile",
        ),
    ]