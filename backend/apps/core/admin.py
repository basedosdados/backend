# -*- coding: utf-8 -*-
from datetime import timedelta

from django import forms
from django.contrib import admin

from .models import TaskExecution


class TaskExecutionForm(forms.ModelForm):
    TASK_NAME_CHOICES = [
        ("sync_database_with_prod", "Sincronizar banco de dados com produção"),
    ]

    task_name = forms.ChoiceField(choices=TASK_NAME_CHOICES)

    class Meta:
        model = TaskExecution
        fields = ["task_name", "execution_time", "duration", "status", "result", "error"]
        widgets = {
            "execution_time": forms.DateTimeInput(attrs={"readonly": "readonly"}),
            "duration": forms.NumberInput(attrs={"readonly": "readonly"}),
            "status": forms.TextInput(attrs={"readonly": "readonly"}),
            "result": forms.Textarea(attrs={"readonly": "readonly"}),
            "error": forms.Textarea(attrs={"readonly": "readonly"}),
        }


class TaskExecutionAdmin(admin.ModelAdmin):
    form = TaskExecutionForm
    list_display = ["task_name", "execution_time", "status", "formatted_duration"]
    readonly_fields = ["execution_time", "duration", "status", "result", "error"]

    def formatted_duration(self, obj):
        duration_seconds = obj.duration
        duration = timedelta(seconds=duration_seconds)
        minutes = duration.seconds // 60
        seconds = duration.seconds % 60
        return f"{minutes} minutes and {seconds} seconds"

    formatted_duration.short_description = "Duration"


admin.site.register(TaskExecution, TaskExecutionAdmin)
