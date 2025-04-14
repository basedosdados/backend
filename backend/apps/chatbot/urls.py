# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    ThreadListView,
    ThreadDetailView,
    MessageView,
    FeedbackView,
    CheckpointView
)

urlpatterns = [
    path("chatbot/threads/", ThreadListView.as_view()),
    path("chatbot/threads/<uuid:thread_id>/", ThreadDetailView.as_view()),
    path("chatbot/threads/<uuid:thread_id>/message", MessageView.as_view()),
    path("chatbot/message-pairs/<uuid:message_pair_id>/feedback", FeedbackView.as_view()),
    path("chatbot/checkpoints/<uuid:thread_id>/", CheckpointView.as_view())
]
