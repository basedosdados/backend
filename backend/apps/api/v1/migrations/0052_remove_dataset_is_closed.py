# Generated by Django 4.2.16 on 2024-11-07 12:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('v1', '0051_add_new_field_dataset'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataset',
            name='is_closed',
        ),
    ]