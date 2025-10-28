# -*- coding: utf-8 -*-
from django.apps import AppConfig
from loguru import logger


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.chatbot"
    verbose_name = "Chatbot"

    def ready(self):
        import backend.apps.chatbot.checks  # noqa: F401
        import chatbot

        # Enable logs from the chatbot package
        logger.enable(chatbot.__name__)
