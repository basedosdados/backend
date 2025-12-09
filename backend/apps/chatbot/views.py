# -*- coding: utf-8 -*-
import os
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from functools import cache
from typing import Any, Iterator, Type, TypedDict, TypeVar

from django.http import StreamingHttpResponse
from google.api_core import exceptions as google_api_exceptions
from graphql_jwt.shortcuts import get_user_by_token
from langchain.chat_models import init_chat_model
from langchain_core.messages import RemoveMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from loguru import logger
from rest_framework import exceptions, status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from backend.apps.chatbot.agent.prompts import SQL_AGENT_SYSTEM_PROMPT
from backend.apps.chatbot.agent.react_agent import ReActAgent
from backend.apps.chatbot.agent.tools import get_tools
from backend.apps.chatbot.agent.types import StateT
from backend.apps.chatbot.feedback_sender import LangSmithFeedbackSender
from backend.apps.chatbot.mock import allow_agent_mock
from backend.apps.chatbot.models import Feedback, MessagePair, Thread
from backend.apps.chatbot.serializers import (
    FeedbackCreateSerializer,
    FeedbackSerializer,
    MessagePairSerializer,
    ThreadCreateSerializer,
    ThreadSerializer,
    UserMessageSerializer,
)
from backend.apps.chatbot.utils.gcloud import get_chatbot_credentials
from backend.apps.chatbot.utils.stream import EventData, StreamEvent, process_chunk

ModelSerializer = TypeVar("ModelSerializer", bound=Serializer)

# Model name/URI. Refer to the LangChain docs for valid names/URIs
# https://python.langchain.com/api_reference/langchain/chat_models/langchain.chat_models.base.init_chat_model.html
MODEL_URI = "google_vertexai:gemini-2.5-flash"

# Gemini models have a ~1 million tokens context window
CONTEXT_WINDOW = 2**20

# Maximum number of tokens allowed at the START of a conversation turn
MAX_TOKENS = CONTEXT_WINDOW // 2

# Generic error message for unexpected errors when calling the agent
ERROR_MESSAGE_UNEXPECTED = (
    "Ops, algo deu errado! Ocorreu um erro inesperado. Por favor, tente novamente. "
    "Se o problema persistir, avise-nos. Obrigado pela paciência!"
)


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

        logger.info(f"Deleting thread {thread_id}")

        try:
            thread.deleted = True
            thread.save()
            with _get_sql_agent() as agent:
                agent.clear_thread(str(thread.id))
            logger.success(f"Thread {thread.id} deleted successfully")
            return Response({"detail": "Thread deleted successfully"})
        except Exception:
            logger.exception(f"Error deleting thread {thread.id}:")
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
            configurable={"thread_id": str(thread.id), "user_id": str(thread.account.uuid)},
        )

        serializer = _validate(request, UserMessageSerializer)

        message = serializer.validated_data["content"]

        return StreamingHttpResponse(
            _stream_sql_agent_response(
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


@contextmanager
def _get_sql_agent() -> Generator[ReActAgent]:
    """Provide a configured ReAct agent.

    Yields:
        Iterator[CompiledGraph]: An instance of `CompiledGraph`.
    """
    db_host = os.environ["DB_HOST"]
    db_port = os.environ["DB_PORT"]
    db_name = os.environ["DB_NAME"]
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]

    conn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    credentials = get_chatbot_credentials()

    model = init_chat_model(
        MODEL_URI,
        api_transport="rest",  # gRPC (the default for ChatVertexAI) is not compatible with gevent
        temperature=0.2,
        credentials=credentials,
    )

    def start_hook(state: StateT):
        messages = state["messages"]

        # For the first message, skip trimming. If it's too long, let it fail.
        if len(messages) == 1:
            return {"messages": []}

        # For subsequent turns, trim chat history to fit within token limits.
        remaining_messages = trim_messages(
            messages,
            token_counter=count_tokens_approximately,  # The accurate counter is too slow.
            max_tokens=MAX_TOKENS,
            strategy="last",
            start_on="human",
            end_on="human",
            include_system=True,
            allow_partial=False,
        )

        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *remaining_messages]}

    with PostgresSaver.from_conn_string(conn) as checkpointer:
        checkpointer.setup()

        sql_agent = ReActAgent(
            model=model,
            tools=get_tools(),
            start_hook=start_hook,
            prompt=SQL_AGENT_SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )

        yield sql_agent


@allow_agent_mock
def _stream_sql_agent_response(message: str, config: ConfigDict, thread: Thread) -> Iterator[str]:
    """Stream agent's execution progress.

    Args:
        message (str): User's input message.
        config (ConfigDict): Configuration for agent execution.
        thread (Thread): Conversation thread.

    Yields:
        Iterator[str]: SSE-formatted event.
    """
    events = []
    agent_state = None

    try:
        logger.info("Calling SQL Agent")
        with _get_sql_agent() as agent:
            for mode, chunk in agent.stream(
                message=message,
                config=config,
                stream_mode=["updates", "values"],
            ):
                if mode == "values":
                    agent_state = chunk
                    continue

                event = process_chunk(chunk)

                if event is not None:
                    if event.type == "final_answer":
                        assistant_message = event.data.content
                        error_message = None
                    events.append(event.model_dump())
                    yield event.to_sse()

        # The last event always contains the agent's final answer,
        # so we use it to save the message pair in the database
        logger.success("SQL Agent called successfully")
    except GraphRecursionError:
        logger.exception(f"Graph recursion error for message {config['run_id']}:")
    except google_api_exceptions.InvalidArgument:
        logger.exception("Agent execution failed with Google API InvalidArgument error:")

        assistant_message = None
        error_message = ERROR_MESSAGE_UNEXPECTED

        if agent_state is not None:
            model = init_chat_model(MODEL_URI, temperature=0)
            total_tokens = model.get_num_tokens_from_messages(agent_state["messages"])

            if total_tokens >= CONTEXT_WINDOW:
                error_message = (
                    "Sua última mensagem ultrapassou o limite de tamanho para esta conversa. "
                    "Por favor, tente dividir sua solicitação em partes menores "
                    "ou inicie uma nova conversa."
                )

        yield StreamEvent(
            type="error", data=EventData(error_details={"message": error_message})
        ).to_sse()
    except Exception:
        logger.exception(f"Unexpected error responding message {config['run_id']}:")
        assistant_message = None
        error_message = ERROR_MESSAGE_UNEXPECTED

        yield StreamEvent(
            type="error", data=EventData(error_details={"message": error_message})
        ).to_sse()

    message_pair = MessagePair.objects.create(
        id=config["run_id"],
        thread=thread,
        model_uri=MODEL_URI,
        user_message=message,
        assistant_message=assistant_message,
        error_message=error_message,
        events=events,
    )
    logger.success(f"Message pair {message_pair.id} saved successfully")

    yield StreamEvent(type="complete", data=EventData(run_id=message_pair.id)).to_sse()


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
