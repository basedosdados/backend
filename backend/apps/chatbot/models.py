# -*- coding: utf-8 -*-
import uuid

from django.db import models

from backend.apps.account.models import Account


class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class MessagePair(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    generated_queries = models.JSONField(null=True, blank=True)
    generated_visual_elements = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    model_uri = models.TextField()

class Feedback(models.Model):
    message_pair = models.OneToOneField(MessagePair, on_delete=models.CASCADE, primary_key=True)
    rating = models.SmallIntegerField(choices=[(-1, "Bad"), (1, "Good")])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
