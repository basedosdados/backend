# -*- coding: utf-8 -*-
from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from .views import (CheckpointView, FeedbackView, MessageView,
                    ThreadDetailView, ThreadListView)

urlpatterns = [
    path('chatbot/token/', TokenObtainPairView.as_view()),
    path('chatbot/token/refresh/', TokenRefreshView.as_view()),
    path("chatbot/threads/", ThreadListView.as_view()),
    path("chatbot/threads/<uuid:thread_id>/", ThreadDetailView.as_view()),
    path("chatbot/threads/<uuid:thread_id>/message/", MessageView.as_view()),
    path("chatbot/message-pairs/<uuid:message_pair_id>/feedback/", FeedbackView.as_view()),
    path("chatbot/checkpoints/<uuid:thread_id>/", CheckpointView.as_view())
]
