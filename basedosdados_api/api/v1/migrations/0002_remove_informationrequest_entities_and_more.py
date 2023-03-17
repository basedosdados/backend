# Generated by Django 4.1.7 on 2023-03-17 16:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="informationrequest",
            name="entities",
        ),
        migrations.RemoveField(
            model_name="observationlevel",
            name="columns",
        ),
        migrations.RemoveField(
            model_name="rawdatasource",
            name="entities",
        ),
        migrations.RemoveField(
            model_name="table",
            name="observation_level",
        ),
        migrations.AddField(
            model_name="column",
            name="observation_level",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="columns",
                to="v1.observationlevel",
            ),
        ),
        migrations.AddField(
            model_name="observationlevel",
            name="information_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="observation_levels",
                to="v1.informationrequest",
            ),
        ),
        migrations.AddField(
            model_name="observationlevel",
            name="raw_data_source",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="observation_levels",
                to="v1.rawdatasource",
            ),
        ),
        migrations.AddField(
            model_name="observationlevel",
            name="table",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="observation_levels",
                to="v1.table",
            ),
        ),
    ]