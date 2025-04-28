# -*- coding: utf-8 -*-
import uuid
from typing import Type, TypeVar

import pydantic
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

PydanticModel = TypeVar("PydanticModel", bound=pydantic.BaseModel)

database = BigQueryDatabase()
assistant = SQLAssistant(database)
assistant.setup()

class ThreadListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> JsonResponse:
        """Retrieve all threads associated with the authenticated user.

        Args:
            request (Request): A Django REST framework `Request` object containing the authenticated user.

        Returns:
            JsonResponse: A JSON response containing a list of serialized threads.
        """
        threads = Thread.objects.filter(account=request.user.id)
        serializer = ThreadSerializer(threads, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self, request: Request) -> JsonResponse:
        """Create a new thread for the authenticated user.

        Args:
            request (Request): A Django REST framework `Request` object containing the authenticated user.

        Returns:
            JsonResponse: A JSON response containing the serialized newly created thread.
        """
        thread = Thread.objects.create(account=request.user)
        serializer = ThreadSerializer(thread)
        return JsonResponse(serializer.data)

class ThreadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, thread_id: uuid.UUID) -> JsonResponse:
        """Retrieve all message pairs associated with a specific thread.

        Args:
            request (Request): A Django REST framework `Request` object.
            thread_id (uuid.UUID): The unique identifier of the thread.

        Returns:
            JsonResponse: A JSON response containing the serialized message pairs.
        """
        thread = _get_thread_by_id(thread_id)
        messages = MessagePair.objects.filter(thread=thread)
        serializer = MessagePairSerializer(messages, many=True)
        return JsonResponse(serializer.data, safe=False)

class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, thread_id: uuid.UUID) -> JsonResponse:
        """Create a message pair for a given thread.

        Args:
            request (Request): A Django REST framework `Request` object containing a user message.
            thread_id (uuid.UUID): The unique identifier for the thread.

        Returns:
            JsonResponse: A JSON response with the serialized message pair object.
        """
        thread_id = str(thread_id)

        user_message = _validate(request, UserMessage)

        thread = _get_thread_by_id(thread_id)

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

class FeedbackListView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request: Request, message_pair_id: uuid.UUID) -> JsonResponse:
        """Create or update a feedback for a given message pair.

        Args:
            request (Request): A Django REST framework `Request` object containing feedback data.
            message_pair_id (uuid.UUID): The unique identifier of the message pair.

        Returns:
            JsonResponse: A JSON response with the serialized feedback object and an appropriate
            HTTP status code (201 for creation, 200 for update).
        """
        data = JSONParser().parse(request)

        serializer = FeedbackCreateSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse(serializer.errors, status=400)

        message_pair = _get_message_pair_by_id(message_pair_id)

        feedback, created = Feedback.objects.update_or_create(
            message_pair=message_pair,
            defaults=serializer.data
        )

        serializer = FeedbackSerializer(feedback)

        status = 201 if created else 200

        return JsonResponse(serializer.data, status=status)

class CheckpointListView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, thread_id: uuid.UUID) -> HttpResponse:
        """Delete all checkpoints associated with a given thread ID.

        Args:
            request (Request): A Django REST framework `Request` object.
            thread_id (uuid.UUID): The unique identifier of the thread.

        Returns:
            HttpResponse: An HTTP response indicating success (200) or failure (500).
        """
        try:
            thread_id = str(thread_id)
            assistant.clear_thread(thread_id)
            return HttpResponse("Checkpoint cleared successfully", status=200)
        except Exception:
            return HttpResponse("Error clearing checkpoint", status=500)

def _get_thread_by_id(thread_id: uuid.UUID) -> Thread:
    """Retrieve a `Thread` object by its ID.

    Args:
        message_pair_id (uuid.UUID): The unique identifier of the `Thread`.

    Raises:
        NotFound: If no `Thread` exists with the given ID.

    Returns:
        Thread: The retrieved `Thread` object.
    """
    try:
        return Thread.objects.get(id=thread_id)
    except Thread.DoesNotExist:
        raise exceptions.NotFound

def _get_message_pair_by_id(message_pair_id: uuid.UUID) -> MessagePair:
    """Retrieve a `MessagePair` object by its ID.

    Args:
        message_pair_id (uuid.UUID): The unique identifier of the `MessagePair`.

    Raises:
        NotFound: If no `MessagePair` exists with the given ID.

    Returns:
        MessagePair: The retrieved `MessagePair` object.
    """
    try:
        return MessagePair.objects.get(id=message_pair_id)
    except MessagePair.DoesNotExist:
        raise exceptions.NotFound

def _validate(request: Request, model: Type[PydanticModel]) -> PydanticModel:
    """Parse and validate a request's JSON payload against a Pydantic model.

    Args:
        request (Request): A Django REST framework `Request` object containing JSON data.
        model (Type[PydanticModel]): A Pydantic model class to validate against.

    Raises:
        exceptions.ValidationError: Raised if the request data fails Pydantic validation.
        (Re-raised as a Django REST framework `ValidationError`).

    Returns:
        PydanticModel: An instance of the provided Pydantic model populated with validated data.
    """
    data = JSONParser().parse(request)

    try:
        return model(**data)
    except pydantic.ValidationError as e:
        raise exceptions.ValidationError(e.errors())
