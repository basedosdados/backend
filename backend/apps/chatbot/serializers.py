import uuid

from rest_framework import serializers

from .models import Feedback, MessagePair, Thread


class FeedbackCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField()
    comment = serializers.CharField(allow_null=True)

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = [field.name for field in Feedback._meta.fields]

class MessagePairSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagePair
        fields = [field.name for field in MessagePair._meta.fields]

class ThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = [field.name for field in Thread._meta.fields]

class UserMessageSerializer(serializers.Serializer):
    id = serializers.CharField(default=str(uuid.uuid4))
    content = serializers.CharField()
