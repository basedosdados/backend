# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    ChatbotAskView,
    ChatInteractionSaveView,
    ClearAssistantMemoryView,
    FeedbackSaveView,
    FeedbackUpdateView,
)

urlpatterns = [
    path(
        "chatbot/ask",
        ChatbotAskView.as_view(),
        name="chatbot_ask",
    ),
    path(
        "chatbot/interactions/save",
        ChatInteractionSaveView.as_view(),
        name="save_chat_interaction",
    ),
    path(
        "chatbot/feedback/save",
        FeedbackSaveView.as_view(),
        name="save_feedback",
    ),
    path(
        "chatbot/feedback/update",
        FeedbackUpdateView.as_view(),
        name="update_feedback",
    ),
    path(
        "chatbot/memory/clear",
        ClearAssistantMemoryView.as_view(),
        name="clear_assistant_memory",
    ),
]
