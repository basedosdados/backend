# Generated by Django 4.2.10 on 2025-02-04

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('v1', '0052_remove_dataset_is_closed'),
    ]

    operations = [
        migrations.RenameField(
            model_name='rawdatasource',
            old_name='required_registration',
            new_name='requires_registration',
        ),
    ]