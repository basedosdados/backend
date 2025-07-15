# -*- coding: utf-8 -*-
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    FeedbackListView,
    MessageListView,
    ThreadDetailView,
    ThreadListView,
)

urlpatterns = [
    path("chatbot/token/", TokenObtainPairView.as_view()),
    path("chatbot/token/refresh/", TokenRefreshView.as_view()),
    path("chatbot/threads/", ThreadListView.as_view()),
    path("chatbot/threads/<uuid:thread_id>/", ThreadDetailView.as_view()),
    path("chatbot/threads/<uuid:thread_id>/messages/", MessageListView.as_view()),
    path("chatbot/message-pairs/<uuid:message_pair_id>/feedbacks/", FeedbackListView.as_view()),
]
