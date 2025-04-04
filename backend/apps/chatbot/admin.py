# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import ChatInteraction, Feedback


class ChatInteractionAdmin(admin.ModelAdmin):
    list_display = [
        "question",
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
        "chat_interaction",
        "rating",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "comment",
        "chat_interaction__question",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]


admin.site.register(ChatInteraction, ChatInteractionAdmin)
admin.site.register(Feedback, FeedbackAdmin)
