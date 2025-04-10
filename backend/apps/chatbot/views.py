# -*- coding: utf-8 -*-
from django.http import JsonResponse
from django.views import View
from backend.apps.chatbot.models import Feedback, MessagePair, Thread


class ChatbotThreadListView(View):
    def get(self, request):
        threads = Thread.objects.filter(user=request.user)
        return JsonResponse(threads)
    
    def post(self, request):
        thread = Thread.objects.create(user=request.user)
        return JsonResponse(thread)


class ThreadDetailView(View):
    def get(self, request, thread_id):
        thread = Thread.objects.get(id=thread_id)
        thread.messages.all()
        return JsonResponse(thread)

class MessageView(View):
    def post(self, request, thread_id):
        thread = Thread.objects.get(id=thread_id)
        question = request.POST.get("message")
        answer = "Resposta do chatbot" # TODO: call chatbot
        # TODO: stream results
        message_pair = MessagePair.objects.create(thread=thread, question=question, answer=answer)
        return JsonResponse(message_pair)


class FeedbackView(View):
    def put(self, request, message_pair_id):
        feedback = Feedback.objects.update_or_create(
            message_pair=message_pair_id,
            rating=request.POST.get("rating"),
            comment=request.POST.get("comment"),
        )
        return JsonResponse(feedback)
