# -*- coding: utf-8 -*-
import uuid

from django.db import models

from backend.apps.account.models import Account


class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class MessagePair(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    model_uri = models.TextField()
    user_message = models.TextField()
    assistant_message = models.TextField()
    generated_queries = models.JSONField(null=True, blank=True)
    generated_chart = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_pair = models.OneToOneField(MessagePair, on_delete=models.CASCADE, primary_key=False)
    rating = models.SmallIntegerField(choices=[(0, "Bad"), (1, "Good")])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
