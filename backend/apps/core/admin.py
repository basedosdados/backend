# -*- coding: utf-8 -*-
from datetime import timedelta

from django.contrib import admin

from .models import TaskExecution


class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = ["task_name", "execution_time", "status", "formatted_duration"]
    readonly_fields = ["task_name", "execution_time", "duration", "status", "result", "error"]

    def has_add_permission(self, request):
        return False

    def formatted_duration(self, obj):
        duration_seconds = obj.duration
        duration = timedelta(seconds=duration_seconds)
        minutes = duration.seconds // 60
        seconds = duration.seconds % 60
        return f"{minutes} minutes and {seconds} seconds"

    formatted_duration.short_description = "Duration"


admin.site.register(TaskExecution, TaskExecutionAdmin)
