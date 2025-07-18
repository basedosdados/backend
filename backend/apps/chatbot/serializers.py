# -*- coding: utf-8 -*-
import uuid

from rest_framework import serializers

from .models import Feedback, MessagePair, Thread


class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["rating", "comment"]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"


class MessagePairSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagePair
        fields = "__all__"


class ThreadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = ["title"]


class ThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = "__all__"


class UserMessageSerializer(serializers.Serializer):
    id = serializers.CharField(default=str(uuid.uuid4))
    content = serializers.CharField()
