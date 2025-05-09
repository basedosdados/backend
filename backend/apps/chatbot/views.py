# -*- coding: utf-8 -*-
import os
import uuid
from functools import cache
from typing import Type, TypeVar

import chromadb
import pydantic
from django.http import HttpResponse, JsonResponse
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from rest_framework import exceptions
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from chatbot.assistants import SQLAssistant, SQLAssistantMessage, UserMessage
from .database import ChatbotDatabase
from .feedback_sender import LangSmithFeedbackSender
from .models import *
from .serializers import *

PydanticModel = TypeVar("PydanticModel", bound=pydantic.BaseModel)

ModelSerializer = TypeVar("ModelSerializer", bound=Serializer)

@cache
def _get_feedback_sender() -> LangSmithFeedbackSender:
    return LangSmithFeedbackSender()

@cache
def _get_sql_assistant() -> SQLAssistant:
    db_url = os.environ["DB_URL"]

    bq_billing_project = os.environ["BILLING_PROJECT_ID"]
    bq_query_project = os.environ["QUERY_PROJECT_ID"]

    chroma_host = os.getenv("CHROMA_HOST")
    chroma_port = os.getenv("CHROMA_PORT")
    chroma_collection = os.getenv("SQL_CHROMA_COLLECTION")

    database = ChatbotDatabase(
        billing_project=bq_billing_project,
        query_project=bq_query_project,
    )

    if chroma_host and chroma_port and chroma_collection:
        chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
        )

        vector_store = Chroma(
            client=chroma_client,
            collection_name=chroma_collection,
            collection_metadata={"hnsw:space": "cosine"},
            embedding_function=OpenAIEmbeddings(
                model="text-embedding-3-small"
            ),
        )
    else:
        vector_store = None

    # Connection kwargs defined according to:
    # https://github.com/langchain-ai/langgraph/issues/2887
    # https://langchain-ai.github.io/langgraph/how-tos/persistence_postgres
    conn_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0
    }

    pool = ConnectionPool(
        conninfo=db_url,
        kwargs=conn_kwargs,
        max_size=8,
        open=False,
    )
    pool.open() # TODO: where to close the pool?

    checkpointer = PostgresSaver(pool)
    checkpointer.setup()

    assistant = SQLAssistant(
        database=database,
        checkpointer=checkpointer,
        vector_store=vector_store
    )

    return assistant

class ThreadListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> JsonResponse:
        """Retrieve all threads associated with the authenticated user.

        Args:
            request (Request): A Django REST framework `Request` object containing the authenticated user.

        Returns:
            JsonResponse: A JSON response containing a list of serialized threads.
        """
        threads = Thread.objects.filter(account=request.user)
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

        serializer = _validate(request, UserMessageSerializer)

        user_message = UserMessage(**serializer.validated_data)

        thread = _get_thread_by_id(thread_id)

        assistant = _get_sql_assistant()

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
        serializer = _validate(request, FeedbackCreateSerializer)

        message_pair = _get_message_pair_by_id(message_pair_id)

        try:
            feedback = Feedback.objects.get(message_pair=message_pair)
            feedback.user_update(serializer.validated_data)
            created = False
        except Feedback.DoesNotExist:
            feedback = Feedback.objects.create(
                message_pair=message_pair, **serializer.validated_data
            )
            created = True

        feedback_sender = _get_feedback_sender()
        feedback_sender.send_feedback(feedback, created)

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
            assistant = _get_sql_assistant()
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

def _validate(request: Request, model_serializer: Type[ModelSerializer]) -> ModelSerializer:
    """
    Parse and validate the JSON payload from a request using a Django REST framework serializer.

    Args:
        request (Request): A Django REST framework `Request` object containing JSON data.
        model_serializer (Type[ModelSerializer]): A serializer class used to validate the data.

    Raises:
        exceptions.ValidationError: If the request data fails serializer validation.

    Returns:
        ModelSerializer: An instance of the serializer populated with validated data.
    """

    data = JSONParser().parse(request)

    serializer = model_serializer(data=data)

    if not serializer.is_valid():
        raise exceptions.ValidationError(serializer.errors)

    return serializer
