# -*- coding: utf-8 -*-
import uuid

from django.db import models

from backend.apps.account.models import User


class ChatInteraction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    generated_queries = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    model_url = models.URLField(null=True, blank=True)


class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_interaction = models.ForeignKey(ChatInteraction, on_delete=models.CASCADE)
    number = models.IntegerField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
