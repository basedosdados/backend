# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import uuid4

from django.db import models

from backend.custom.model import BaseModel


class Metadata(BaseModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    id = models.UUIDField(primary_key=True, default=uuid4)
    key = models.JSONField(default=dict, blank=False, null=False)
    value = models.JSONField(default=dict, blank=False, null=False)


class TaskExecution(models.Model):
    task_name = models.CharField(max_length=255)
    execution_time = models.DateTimeField(default=datetime.now)
    duration = models.FloatField(default=0)
    status = models.CharField(max_length=100, default="running")
    result = models.TextField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)

    class Meta:
        """Meta definition for TaskExecution."""

        verbose_name = "Tarefa executada"
        verbose_name_plural = "Tarefas executadas"
        ordering = ["-execution_time"]
