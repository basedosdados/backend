# Generated by Django 4.2.20 on 2025-04-10 15:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MessagePair',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('question', models.TextField()),
                ('answer', models.TextField()),
                ('generated_queries', models.JSONField(blank=True, null=True)),
                ('generated_visual_elements', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('model_uri', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('message_pair', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='chatbot.messagepair')),
                ('rating', models.SmallIntegerField(choices=[(-1, 'Bad'), (1, 'Good')])),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Thread',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='messagepair',
            name='thread',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chatbot.thread'),
        ),
    ]
