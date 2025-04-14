# -*- coding: utf-8 -*-
import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

# TODO: add authentication (using this login_required decorator + checking user id)
# TODO: add error handling (404 wrong thread if, etc...)
# TODO: To test this, create a test user in a migration

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from backend.apps.chatbot.models import Feedback, MessagePair, Thread
from chatbot.assistants import SQLAssistant, SQLAssistantMessage, UserMessage
from chatbot.databases import BigQueryDatabase


database = BigQueryDatabase()

assistant = SQLAssistant(database=database)


class ThreadListView(View):
    def get(self, request: HttpRequest, *args, **kwargs):
        threads = Thread.objects.filter(account=request.user)
        return JsonResponse({"threads": [thread.to_dict() for thread in threads]})

    def post(self, request: HttpRequest, *args, **kwargs):
        thread = Thread.objects.create(account=request.user)
        return JsonResponse(thread.to_dict())

class ThreadDetailView(View):
    def get(self, request: HttpRequest, thread_id: str, *args, **kwargs):
        try:
            thread = Thread.objects.get(id=thread_id)
        except Thread.DoesNotExist:
            return HttpResponse(404)

        if thread.account.uuid != request.user.id:
            return JsonResponse(
                data={"error": "You are not authorized to access this thread"},
                status=403
            )

        messages = MessagePair.objects.filter(thread=thread)

        return JsonResponse({"messages": [message.to_dict() for message in messages]})

class MessageView(View):
    def post(self, request: HttpRequest, thread_id: str, *args, **kwargs):
        thread = Thread.objects.get(id=thread_id)

        if thread.account.uuid != request.user.id:
            return JsonResponse(
                data={"error": "You are not authorized to access this thread"},
                status=403
            )

        user_message = json.loads(request.body.decode("utf-8"))
        user_message = UserMessage(**user_message)

        assistant_response: SQLAssistantMessage = assistant.invoke(
            message=user_message,
            thread_id=thread_id
        )

        # TODO (nice to have): stream results
        message_pair = MessagePair.objects.create(
            id=assistant_response.id,
            thread=thread_id,
            model_uri=assistant_response.model_uri,
            user_message=user_message.content,
            assistant_message=assistant_response.content,
            generated_queries=assistant_response.sql_queries,
        )

        return JsonResponse(message_pair)

class FeedbackView(View):
    def put(self, request: HttpRequest, message_pair_id: str, *args, **kwargs):
        message_pair = MessagePair.objects.get(id=message_pair_id)

        if message_pair.thread.account.uuid != request.user.id:
            return JsonResponse(
                data={"error": "You are not authorized to access this thread"},
                status=403
            )

        feedback: dict = json.loads(request.body.decode("utf-8"))

        feedback = Feedback.objects.update_or_create(
            message_pair=message_pair_id,
            rating=feedback["rating"],
            comment=feedback["comment"],
        )

        return JsonResponse(feedback)

class CheckpointView(View):
    def delete(self, request: HttpRequest, thread_id: str, *args, **kwargs):
        thread = Thread.objects.get(id=thread_id)

        if thread.account.uuid != request.user.id:
            return JsonResponse(
                data={"error": "You are not authorized to access this thread"},
                status=403
            )

        assistant.clear_thread(thread_id)

        return HttpResponse(200)
