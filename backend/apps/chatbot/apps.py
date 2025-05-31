# -*- coding: utf-8 -*-
from django.apps import AppConfig
from loguru import logger


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.chatbot"
    verbose_name = "Chatbot"

    def ready(self):
        # Enable logs from the chatbot package
        import chatbot
        logger.enable(chatbot.__name__)
