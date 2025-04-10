# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Feedback, MessagePair, Thread


class ThreadAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "created_at",
    ]

class MessagePairAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "question",
        "answer",
        "created_at",
    ]
    search_fields = [
        "question",
        "answer",
    ]
    readonly_fields = [
        "created_at",
    ]
    ordering = ["-created_at"]


class FeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "message_pair_id",
        "rating",
        "created_at",
        "updated_at",
    ]
    search_fields = [
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]


admin.site.register(Thread, ThreadAdmin)
admin.site.register(MessagePair, MessagePairAdmin)
admin.site.register(Feedback, FeedbackAdmin)
