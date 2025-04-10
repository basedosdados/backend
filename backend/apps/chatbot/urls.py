# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    ChatbotThreadListView,
    ThreadDetailView,
    MessageView,
    FeedbackView,
)

urlpatterns = [
    path(
        "chatbot/threads/",
        ChatbotThreadListView.as_view(),
        name="chatbot_threads",
    ),
    path(
        "chatbot/threads/<uuid:thread_id>/",
        ThreadDetailView.as_view(),
        name="chatbot_thread",
    ),
    path(
        "chatbot/threads/<uuid:thread_id>/message",
        MessageView.as_view(),
        name="chatbot_thread",
    ),
    path(
        "chatbot/message-pairs/<uuid:message_pair_id>/feedback",
        FeedbackView.as_view(),
        name="chatbot_message_pair_feedback",
    )
]
