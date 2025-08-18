# -*- coding: utf-8 -*-
import json
import os
import uuid
from contextlib import contextmanager
from functools import cache
from typing import Any, Iterator, Type, TypedDict, TypeVar

from django.http import StreamingHttpResponse
from graphql_jwt.shortcuts import get_user_by_token
from langchain.chat_models import init_chat_model
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_postgres import PGVector
from langgraph.checkpoint.postgres import PostgresSaver
from loguru import logger
from rest_framework import exceptions, status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from backend.apps.chatbot.context_provider import PostgresContextProvider
from backend.apps.chatbot.feedback_sender import LangSmithFeedbackSender
from backend.apps.chatbot.models import Feedback, MessagePair, Thread
from backend.apps.chatbot.serializers import (
    FeedbackCreateSerializer,
    FeedbackSerializer,
    MessagePairSerializer,
    ThreadCreateSerializer,
    ThreadSerializer,
    UserMessageSerializer,
)
from backend.apps.chatbot.utils.stream import process_chunk
from chatbot.assistants import SQLAssistant, format_sql_agent_response
from chatbot.formatters import SQLPromptFormatter

ModelSerializer = TypeVar("ModelSerializer", bound=Serializer)


# Model name/URI. Refer to the LangChain docs for valid names/URIs
# https://python.langchain.com/api_reference/langchain/chat_models/langchain.chat_models.base.init_chat_model.html
MODEL_URI = os.environ["MODEL_URI"]


class ConfigDict(TypedDict):
    run_id: str
    recursion_limit: int
    configurable: dict[str, Any]


class TokenBridgeView(APIView):
    """Token bridging endpoint to convert main website JWT tokens to chatbot tokens."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        """Convert main website JWT token to chatbot token.

        Args:
            request (Request): Contains main_token in request body

        Returns:
            Response: Chatbot access token if conversion successful
        """
        try:
            main_token = request.data.get("main_token")
            if not main_token:
                return Response(
                    {"detail": "main_token is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Validate the main website's JWT token
            try:
                user = get_user_by_token(main_token)
            except Exception:
                return Response(
                    {"detail": "Invalid main token"}, status=status.HTTP_401_UNAUTHORIZED
                )

            # Check if user has chatbot access
            if not user.has_chatbot_access:
                return Response(
                    {"detail": "User does not have chatbot access"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Generate chatbot-compatible token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return Response(
                {
                    "access": access_token,
                    "refresh": str(refresh),
                    "user_id": user.id,
                    "email": user.email,
                }
            )

        except Exception as e:
            logger.error(f"Token bridge error: {str(e)}")
            return Response(
                {"detail": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ThreadListView(APIView):
    permission_classes = [IsAuthenticated]
    ordering_fields = {"created_at", "-created_at"}

    def get(self, request: Request) -> Response:
        """Retrieve all threads associated with the authenticated user.

        Args:
            request (Request): A Django REST framework `Request` object
            containing the authenticated user.

        Returns:
            Response: A JSON response containing a list of serialized threads.
        """
        threads = Thread.objects.filter(account=request.user, deleted=False)

        field = request.query_params.get("order_by")

        if field is not None:
            if field not in self.ordering_fields:
                return Response(
                    {"detail": f"Invalid order_by field: {field}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            threads = threads.order_by(field)

        serializer = ThreadSerializer(threads, many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        """Create a new thread for the authenticated user.

        Args:
            request (Request): A Django REST framework `Request` object
            containing the authenticated user.

        Returns:
            Response: A JSON response containing the serialized newly created thread.
        """
        serializer = _validate(request, ThreadCreateSerializer)

        title = serializer.validated_data["title"]

        thread = Thread.objects.create(account=request.user, title=title)
        serializer = ThreadSerializer(thread)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ThreadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, thread_id: uuid.UUID) -> Response:
        """Soft delete a thread and hard delete all its checkpoints.

        Args:
            request (Request): A Django REST framework `Request` object.
            thread_id (uuid.UUID): The unique identifier of the thread.

        Returns:
            Response: A JSON response indicating success (200) or failure (500).
        """
        thread = _get_thread_by_id(thread_id)

        try:
            thread.deleted = True
            thread.save()
            with _get_sql_assistant() as assistant:
                assistant.clear_thread(str(thread_id))
            return Response({"detail": "Thread deleted successfully"})
        except Exception:
            return Response(
                {"detail": "Error deleting thread"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]
    ordering_fields = {"created_at", "-created_at"}

    def get(self, request: Request, thread_id: uuid.UUID) -> Response:
        """Retrieve all message pairs associated with a specific thread.

        Args:
            request (Request): A Django REST framework `Request` object.
            thread_id (uuid.UUID): The unique identifier of the thread.

        Returns:
            Response: A JSON response containing the serialized message pairs.
        """
        thread = _get_thread_by_id(thread_id)

        message_pairs = MessagePair.objects.filter(thread=thread)

        field = request.query_params.get("order_by")

        if field is not None:
            if field not in self.ordering_fields:
                return Response(
                    {"detail": f"Invalid order_by field: {field}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            message_pairs = message_pairs.order_by(field)

        serializer = MessagePairSerializer(message_pairs, many=True)
        return Response(serializer.data)

    def post(self, request: Request, thread_id: uuid.UUID) -> Response:
        """Create a message pair for a given thread.

        Args:
            request (Request): A Django REST framework `Request` object containing a user message.
            thread_id (uuid.UUID): The unique identifier for the thread.

        Returns:
            Response: A JSON response with the serialized message pair object.
        """
        thread = _get_thread_by_id(thread_id)

        run_id = str(uuid.uuid4())

        config = ConfigDict(
            run_id=run_id,
            recursion_limit=32,
            configurable={
                "thread_id": str(thread.id),
            },
        )

        serializer = _validate(request, UserMessageSerializer)

        message = serializer.validated_data["content"]

        return StreamingHttpResponse(
            _stream_sql_assistant_response(
                message=message,
                config=config,
                thread=thread,
            ),
            status=status.HTTP_201_CREATED,
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
            content_type="text/event-stream",
        )


class FeedbackListView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request: Request, message_pair_id: uuid.UUID) -> Response:
        """Create or update a feedback for a given message pair.

        Args:
            request (Request): A Django REST framework `Request` object containing feedback data.
            message_pair_id (uuid.UUID): The unique identifier of the message pair.

        Returns:
            Response: A JSON response with the serialized feedback object and an appropriate
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

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(serializer.data, status=status_code)


@cache
def _get_feedback_sender() -> LangSmithFeedbackSender:
    """Provide a `LangSmithFeedbackSender` feedback sender.

    Returns:
        LangSmithFeedbackSender: An instance of `LangSmithFeedbackSender`.
    """
    return LangSmithFeedbackSender()


@cache
def _get_context_provider(connection: str) -> PostgresContextProvider:
    """Provide a configured `PostgresContextProvider` context provider.

    Args:
        connection (str): A vector database connection for providing few-shot examples.

    Returns:
        PostgresContextProvider: An instance of `PostgresContextProvider`.
    """
    bq_billing_project = os.environ["BILLING_PROJECT_ID"]
    bq_query_project = os.environ["QUERY_PROJECT_ID"]

    embedding_model = os.getenv("EMBEDDING_MODEL")
    pgvector_collection = os.getenv("PGVECTOR_COLLECTION")

    if embedding_model and pgvector_collection:
        embeddings = VertexAIEmbeddings(embedding_model)

        vector_store = PGVector(
            embeddings=embeddings,
            connection=connection,
            collection_name=pgvector_collection,
            use_jsonb=True,
        )
    else:
        vector_store = None

    context_provider = PostgresContextProvider(
        billing_project=bq_billing_project,
        query_project=bq_query_project,
        metadata_vector_store=vector_store,
        top_k=5,
    )

    return context_provider


@contextmanager
def _get_sql_assistant():
    """Provide a configured `SQLAssistant`.

    Yields:
        Iterator[SQLAssistant]: An instance of `SQLAssistant`.
    """
    db_host = os.environ["DB_HOST"]
    db_port = os.environ["DB_PORT"]
    db_name = os.environ["DB_NAME"]
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]

    conn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    context_provider = _get_context_provider(conn)

    prompt_formatter = SQLPromptFormatter(vector_store=None)

    with PostgresSaver.from_conn_string(conn) as checkpointer:
        checkpointer.setup()

        model = init_chat_model(MODEL_URI, temperature=0)

        assistant = SQLAssistant(
            model=model,
            context_provider=context_provider,
            prompt_formatter=prompt_formatter,
            checkpointer=checkpointer,
        )

        yield assistant


def _stream_sql_assistant_response(
    message: str, config: ConfigDict, thread: Thread
) -> Iterator[str]:
    """Stream SQLAssistant's execution progress.

    Args:
        message (str): User's input message.
        config (ConfigDict): Configuration for the assistant's execution.
        thread (Thread): Unique identifier for the conversation thread.

    Yields:
        Iterator[str]: JSON string containing the streaming status and the current step data.
    """
    steps = []
    last_chunk = None

    try:
        logger.info("Calling SQLAssistant...")
        with _get_sql_assistant() as assistant:
            for mode, chunk in assistant.stream(
                message=message,
                config=config,
                stream_mode=["updates", "values"],
                rewrite_query=True,
            ):
                last_chunk = chunk

                # Skip "values" chunks during streaming. We only need the final one at the end,
                # as it contains the SQL Agent's final state.
                if mode == "values":
                    continue

                step = process_chunk(chunk)

                if step is None:
                    continue

                steps.append(step.model_dump())

                yield json.dumps({"status": "running", "data": step.model_dump_json()}) + "\n\n"

        # The last chunk represents the SQLAgent's final state,
        # so we format it as the final response for the user.
        response = format_sql_agent_response(last_chunk)
        response["error_message"] = None
    except Exception:
        logger.exception(f"Error responding message {config['run_id']}:")
        response = {
            "error_message": (
                "Ops, algo deu errado! Ocorreu um erro inesperado. Por favor, tente novamente. "
                "Se o problema persistir, avise-nos. Obrigado pela paciência!"
            ),
            "content": None,
            "sql_queries": None,
        }

    logger.success("SQLAssistant called successfully")

    response["id"] = config["run_id"]

    message_pair = MessagePair.objects.create(
        id=response["id"],
        thread=thread,
        model_uri=MODEL_URI,
        user_message=message,
        assistant_message=response["content"],
        error_message=response["error_message"],
        generated_queries=response["sql_queries"],
        steps=steps,
    )

    yield (
        json.dumps(
            {
                "status": "complete",
                "data": {
                    "id": message_pair.id,
                    "user_message": message_pair.user_message,
                    "assistant_message": message_pair.assistant_message,
                    "error_message": message_pair.error_message,
                    "generated_queries": message_pair.generated_queries,
                },
            }
        )
        + "\n\n"
    )


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
        return Thread.objects.get(id=thread_id, deleted=False)
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
