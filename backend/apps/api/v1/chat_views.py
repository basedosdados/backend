from django.http import HttpResponse
from django.views import View

class ChatView(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse("Hello")