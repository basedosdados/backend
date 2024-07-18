# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import TaskExecution


class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = ["task_name", "execution_time", "status", "duration"]
    readonly_fields = ["task_name", "execution_time", "duration", "status", "result", "error"]

    def has_add_permission(self, request):
        return False


admin.site.register(TaskExecution, TaskExecutionAdmin)
