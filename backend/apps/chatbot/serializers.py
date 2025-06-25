# -*- coding: utf-8 -*-
import uuid

from rest_framework import serializers

from .models import Feedback, MessagePair, Thread


class FeedbackCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField()
    comment = serializers.CharField(allow_null=True)


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"


class MessagePairSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagePair
        fields = "__all__"


class ThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = "__all__"


class UserMessageSerializer(serializers.Serializer):
    id = serializers.CharField(default=str(uuid.uuid4))
    content = serializers.CharField()
