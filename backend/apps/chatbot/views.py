# -*- coding: utf-8 -*-
from django.http import HttpResponse, JsonResponse
from rest_framework import exceptions
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from chatbot.assistants import SQLAssistant, SQLAssistantMessage, UserMessage
from chatbot.databases import BigQueryDatabase

from .models import *
from .serializers import *

# TODO: add authentication (using this login_required decorator + checking user id)
# TODO: add error handling (404 wrong thread if, etc...)
# TODO: To test this, create a test user in a migration

database = BigQueryDatabase()

assistant = SQLAssistant(database=database)

def get_thread_by_id(thread_id: str) -> Thread:
    try:
        return Thread.objects.get(id=thread_id)
    except Thread.DoesNotExist:
        raise exceptions.NotFound

def get_message_pair_by_id(message_pair_id: str) -> MessagePair:
    try:
        return MessagePair.objects.get(id=message_pair_id)
    except MessagePair.DoesNotExist:
        raise exceptions.NotFound

class ThreadListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        threads = Thread.objects.filter(account=request.user.id)
        serializer = ThreadSerializer(threads, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self, request: Request):
        thread = Thread.objects.create(account=request.user)
        serializer = ThreadSerializer(thread)
        return JsonResponse(serializer.data)

class ThreadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, thread_id: str):
        thread = get_thread_by_id(thread_id)
        messages = MessagePair.objects.filter(thread=thread)
        serializer = MessagePairSerializer(messages, many=True)
        return JsonResponse(serializer.data, safe=False)

class MessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, thread_id: str):
        data = JSONParser().parse(request)

        serializer = UserMessageSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse(serializer.errors, status=400)

        user_message = UserMessage(**serializer.data)

        thread = get_thread_by_id(thread_id)

        assistant_response: SQLAssistantMessage = assistant.invoke(
            message=user_message,
            thread_id=thread_id
        )

        # TODO (nice to have): stream results
        message_pair = MessagePair.objects.create(
            id=assistant_response.id,
            thread=thread,
            model_uri=assistant_response.model_uri,
            user_message=user_message.content,
            assistant_message=assistant_response.content,
            generated_queries=assistant_response.sql_queries,
        )

        serializer = MessagePairSerializer(message_pair)

        return JsonResponse(serializer.data, status=201)

class FeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request: Request, message_pair_id: str):
        data = JSONParser().parse(request)

        serializer = FeedbackCreateSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse(serializer.errors, status=400)

        message_pair = get_message_pair_by_id(message_pair_id)

        feedback, created = Feedback.objects.update_or_create(
            message_pair=message_pair,
            defaults=serializer.data
        )

        serializer = FeedbackSerializer(feedback)

        status = 201 if created else 200

        return JsonResponse(serializer.data, status=status)

class CheckpointView(APIView):
    def delete(self, request: Request, thread_id: str):
        try:
            assistant.clear_thread(thread_id)
            return HttpResponse("Checkpoint cleared successfully", status=200)
        except Exception:
            return HttpResponse("Error clearing checkpoint", status=500)
