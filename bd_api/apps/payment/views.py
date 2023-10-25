# -*- coding: utf-8 -*-
from json import JSONDecodeError, loads

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from djstripe.models import Customer as DJStripeCustomer
from djstripe.models import Subscription as DJStripeSubscription
from loguru import logger
from stripe import Customer as StripeCustomer

from bd_api.apps.account.models import Account


@csrf_exempt
class StripeCustomerView(View):
    """Update stripe customer fields:
    - name
    - email
    - address
      - line1: "Rua Augusta, 100"
      - city: "São Paulo"
      - state: "SP"
      - country: "BR"
      - postal_code: "01304-000"
    """

    def put(self, request, account_id):
        try:
            body = loads(request.body)
            assert "name" in body
            assert "email" in body
            assert "address" in body

            account = Account.objects.get(id=account_id)
            customer: DJStripeCustomer = account.djstripe_customers[0]
            customer = StripeCustomer.modify(customer.id, **body)

            return JsonResponse(customer.values())
        except (JSONDecodeError, KeyError) as e:
            logger.error(e)
            return JsonResponse({}, status=400)
        except Exception as e:
            logger.error(e)
            return JsonResponse({"error": str(e)}, status=422)


@csrf_exempt
class StripeSubscriptionView(View):
    """Create a stripe subscription"""

    def post(self, request, account_id, price_id):
        try:
            account = Account.objects.get(id=account_id)
            customer: DJStripeCustomer = account.djstripe_customers[0]
            subscription: DJStripeSubscription = customer.subscribe(
                price=price_id,
                payment_behaviour="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
            )
            return JsonResponse(
                {
                    "subscription_id": subscription.id,
                    "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                }
            )
        except (JSONDecodeError, KeyError) as e:
            logger.error(e)
            return JsonResponse({}, status=400)
        except Exception as e:
            logger.error(e)
            return JsonResponse({"error": str(e)}, status=422)


# Reference
# https://stripe.com/docs/billing/subscriptions/build-subscriptions?ui=elementsf
