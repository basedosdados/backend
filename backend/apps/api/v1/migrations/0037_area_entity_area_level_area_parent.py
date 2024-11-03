# Generated by Django 4.2.16 on 2024-11-03 01:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('v1', '0036_datetimerange_units'),
    ]

    operations = [
        migrations.AddField(
            model_name='area',
            name='entity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='areas', to='v1.entity'),
        ),
        migrations.AddField(
            model_name='area',
            name='level',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='area',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='v1.area'),
        ),
    ]
