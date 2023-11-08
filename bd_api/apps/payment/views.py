# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt


@method_decorator(csrf_exempt, "dispatch")
@method_decorator(login_required, "dispatch")
class StripeCustomerSubscriptionView(View):
    def post(self, request: HttpRequest, account_id: str, subscription_id: str):
        """Add customer to a stripe subscription"""
        ...

    def delete(self, request: HttpRequest, account_id: str, subscription_id: str):
        """Remove customer from a stripe subscription"""
        ...


# Reference
# https://stripe.com/docs/billing/subscriptions/build-subscriptions?ui=elementsf
