# -*- coding: utf-8 -*-
from django.http import JsonResponse
from django.views import View
from backend.apps.chatbot.models import Feedback, MessagePair, Thread

# TODO: add authentication (using this login_required decorator + checking user id)
# TODO: add error handling (404 wrong thread if, etc...)
# TODO: To test this, create a test user in a migration

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class ChatbotThreadListView(View):
    def get(self, request, *args, **kwargs):
        threads = Thread.objects.filter(account=request.user.id)
        return JsonResponse([thread.to_dict() for thread in threads], safe=False)
    
    def post(self, request, *args, **kwargs):
        thread = Thread.objects.create(account=request.user.id)
        return JsonResponse(thread.to_dict())

class ThreadDetailView(View):
    def get(self, request, thread_id, *args, **kwargs):
        thread = Thread.objects.get(id=thread_id)
        if thread.account != request.user.id:
            return JsonResponse({"error": "You are not authorized to access this thread"}, status=403)
        messages = thread.messages.all()
        return JsonResponse(messages)

class MessageView(View):
    def post(self, request, thread_id, *args, **kwargs):
        thread = Thread.objects.get(id=thread_id)
        if thread.account_id != request.user.id:
            return JsonResponse({"error": "You are not authorized to access this thread"}, status=403)
        question = request.POST.get("message")
        answer = "Resposta do chatbot" # TODO: call chatbot
        # TODO (nice to have): stream results
        message_pair = MessagePair.objects.create(thread=thread, question=question, answer=answer)
        return JsonResponse(message_pair)

class FeedbackView(View):
    def put(self, request, message_pair_id, *args, **kwargs):
        message_pair = MessagePair.objects.get(id=message_pair_id)
        if message_pair.thread.account_id != request.user.id:
            return JsonResponse({"error": "You are not authorized to access this thread"}, status=403)
        feedback = Feedback.objects.update_or_create(
            message_pair=message_pair_id,
            rating=request.POST.get("rating"),
            comment=request.POST.get("comment"),
        )
        return JsonResponse(feedback)