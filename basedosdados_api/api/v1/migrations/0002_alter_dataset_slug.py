# Generated by Django 4.1.7 on 2023-03-16 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dataset",
            name="slug",
            field=models.SlugField(max_length=255),
        ),
    ]
