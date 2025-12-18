# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Feedback, MessagePair, Thread


class ThreadAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Thread._meta.fields]
    readonly_fields = list_display
    search_fields = [
        "id",
        "account__email",
    ]
    ordering = ["-created_at"]


class MessagePairAdmin(admin.ModelAdmin):
    list_display = [field.name for field in MessagePair._meta.fields]
    readonly_fields = list_display
    search_fields = [
        "id",
        "thread__id",
        "user_message",
        "assistant_message",
    ]
    ordering = ["-created_at"]


class FeedbackAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Feedback._meta.fields]
    readonly_fields = list_display
    search_fields = [
        "id",
        "message_pair__id",
    ]
    ordering = ["-created_at"]


admin.site.register(Thread, ThreadAdmin)
admin.site.register(MessagePair, MessagePairAdmin)
admin.site.register(Feedback, FeedbackAdmin)
