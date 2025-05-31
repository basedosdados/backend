# -*- coding: utf-8 -*-
import uuid

import pytest
from rest_framework.test import APIClient

from backend.apps.account.models import Account
from backend.apps.chatbot import views
from backend.apps.chatbot.models import Feedback, MessagePair, Thread
from chatbot.assistants import SQLAssistantMessage


class MockSQLAssistant:
    def __init__(self, *args, **kwargs):
        ...

    def invoke(self, *args, **kwargs):
        return SQLAssistantMessage(model_uri="google/gemini-2.0-flash", content="mock response")

    def clear_thread(self, *args, **kwargs):
        ...


class MockLangSmithFeedbackSender:
    def __init__(self, *args, **kwargs):
        ...

    def send_feedback(self, *args, **kwargs):
        ...


@pytest.fixture
def mock_email() -> str:
    return "mockemail@mockdomain.com"


@pytest.fixture
def mock_password() -> str:
    return "mockpassword"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_user(mock_email: str, mock_password: str) -> Account:
    return Account.objects.create(
        email=mock_email,
        password=mock_password,
        is_active=True,
        has_chatbot_access=True,
    )


@pytest.fixture
def access_token(client: APIClient, mock_email: str, mock_password: str, auth_user: Account) -> str:
    response = client.post(
        path="/chatbot/token/", data={"email": mock_email, "password": mock_password}
    )
    assert response.status_code == 200

    return response.data["access"]


@pytest.fixture
def auth_client(access_token) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client


@pytest.mark.django_db
def test_token_view_authorized(client: APIClient, mock_email: str, mock_password: str):
    _ = Account.objects.create(
        email=mock_email,
        password=mock_password,
        is_active=True,
        has_chatbot_access=True,
    )

    response = client.post(
        path="/chatbot/token/", data={"email": mock_email, "password": mock_password}
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_token_view_unauthorized(client: APIClient, mock_email: str, mock_password: str):
    _ = Account.objects.create(
        email=mock_email,
        password=mock_password,
        is_active=True,
        # has_chatbot_access = False - has_chatbot_access is False by default
    )

    response = client.post(
        path="/chatbot/token/", data={"email": mock_email, "password": mock_password}
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_token_view_user_not_registered(client: APIClient, mock_email: str, mock_password: str):
    response = client.post(
        path="/chatbot/token/", data={"email": mock_email, "password": mock_password}
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_thread_list_view_get(auth_client: APIClient):
    response = auth_client.get("/chatbot/threads/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_thread_list_view_post(auth_client: APIClient):
    response = auth_client.post("/chatbot/threads/")
    assert response.status_code == 201

    thread_attrs = response.json()

    assert "id" in thread_attrs
    assert "account" in thread_attrs
    assert "created_at" in thread_attrs
    assert Thread.objects.get(id=thread_attrs["id"])


@pytest.mark.django_db
def test_thread_detail_view_get(auth_client: APIClient, auth_user: Account):
    thread = Thread.objects.create(account=auth_user)

    response = auth_client.get(f"/chatbot/threads/{thread.id}/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_thread_detail_view_get_not_found(auth_client: APIClient):
    response = auth_client.get(f"/chatbot/threads/{uuid.uuid4()}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_message_list_view_post(monkeypatch, auth_client: APIClient, auth_user: Account):
    monkeypatch.setattr(views, "SQLAssistant", MockSQLAssistant)

    thread = Thread.objects.create(account=auth_user)

    response = auth_client.post(
        path=f"/chatbot/threads/{thread.id}/messages/",
        data={"id": str(uuid.uuid4()), "content": "mock message"},
        format="json",
    )

    assert response.status_code == 201

    response = auth_client.post(
        path=f"/chatbot/threads/{thread.id}/messages/",
        data={"content": "mock message"},
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_message_list_view_post_bad_request(auth_client: APIClient, auth_user: Account):
    thread = Thread.objects.create(account=auth_user)

    response = auth_client.post(
        path=f"/chatbot/threads/{thread.id}/messages/",
        data={"id": str(uuid.uuid4())},
        format="json",
    )

    assert response.status_code == 400

    response = auth_client.post(
        path=f"/chatbot/threads/{thread.id}/messages/",
        data={"id": str(uuid.uuid4()), "content": []},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_message_list_view_post_not_found(auth_client: APIClient):
    response = auth_client.post(
        path=f"/chatbot/threads/{uuid.uuid4()}/messages/",
        data={"id": str(uuid.uuid4()), "content": "mock message"},
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_feedback_list_view_put_create(monkeypatch, auth_client: APIClient, auth_user: Account):
    monkeypatch.setattr(views, "LangSmithFeedbackSender", MockLangSmithFeedbackSender)

    thread = Thread.objects.create(account=auth_user)

    message_pairs = [
        MessagePair.objects.create(
            thread=thread,
            model_uri="google/gemini-2.0-flash",
            user_message="mock message",
            assistant_message="mock response",
        )
        for _ in range(2)
    ]

    response = auth_client.put(
        path=f"/chatbot/message-pairs/{message_pairs[0].id}/feedbacks/",
        data={"rating": 1, "comment": "good"},
        format="json",
    )

    assert response.status_code == 201

    response = auth_client.put(
        path=f"/chatbot/message-pairs/{message_pairs[1].id}/feedbacks/",
        data={"rating": 1, "comment": None},
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_feedback_list_view_put_update(monkeypatch, auth_client: APIClient, auth_user: Account):
    monkeypatch.setattr(views, "LangSmithFeedbackSender", MockLangSmithFeedbackSender)

    thread = Thread.objects.create(account=auth_user)

    message_pair = MessagePair.objects.create(
        thread=thread,
        model_uri="google/gemini-2.0-flash",
        user_message="mock message",
        assistant_message="mock response",
    )

    _ = Feedback.objects.create(message_pair=message_pair, rating=0, comment="bad")

    response = auth_client.put(
        path=f"/chatbot/message-pairs/{message_pair.id}/feedbacks/",
        data={"rating": 1, "comment": "good"},
        format="json",
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_feedback_list_view_put_bad_request(auth_client: APIClient, auth_user: Account):
    thread = Thread.objects.create(account=auth_user)

    message_pair = MessagePair.objects.create(
        thread=thread,
        model_uri="google/gemini-2.0-flash",
        user_message="mock message",
        assistant_message="mock response",
    )

    response = auth_client.put(
        path=f"/chatbot/message-pairs/{message_pair.id}/feedbacks/",
        data={"comment": "good"},
        format="json",
    )

    assert response.status_code == 400

    response = auth_client.put(
        path=f"/chatbot/message-pairs/{message_pair.id}/feedbacks/",
        data={"rating": 1, "comment": []},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_feedback_list_view_put_not_found(auth_client: APIClient, auth_user: Account):
    response = auth_client.put(
        path=f"/chatbot/message-pairs/{uuid.uuid4()}/feedbacks/",
        data={"rating": 1, "comment": "good"},
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_checkpoint_list_view_delete(auth_client: APIClient, auth_user: Account):
    thread = Thread.objects.create(account=auth_user)
    response = auth_client.delete(f"/chatbot/checkpoints/{thread.id}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_checkpoint_list_view_delete_not_found(auth_client: APIClient):
    response = auth_client.delete(f"/chatbot/checkpoints/{uuid.uuid4()}/")
    assert response.status_code == 404
