# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import TaskExecution
from .tasks import sync_database_with_prod


@receiver(post_save, sender=TaskExecution)
def task_execution_post_save(sender, instance, created, **kwargs):
    if created:
        sync_database_with_prod()
