# -*- coding: utf-8 -*-
from json import JSONDecodeError, loads

from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpRequest, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from djstripe.models import Customer as DJStripeCustomer
from djstripe.models import Price as DJStripePrice
from djstripe.models import Subscription as DJStripeSubscription
from loguru import logger
from stripe import Customer as StripeCustomer

from bd_api.apps.account.models import Account


class StripePriceView(View):
    @csrf_exempt
    def get(self, request: HttpRequest):
        """Get stripe prices"""
        price = (
            DJStripePrice.objects.select_related("product")
            .filter(active=True)
            .filter(product__active=True)
            .filter(product__name__icontains="bd pro")
            .annotate(price_id=F("id"))
            .annotate(amount=F("unit_amount") / 100)
            .annotate(product_name=F("product__name"))
            .all()
        )
        values = price.values(
            "price_id",
            "product_name",
            "amount",
        )
        return JsonResponse({"price": list(values)})


class StripeCustomerView(View):
    @csrf_exempt
    @login_required
    def post(self, request: HttpRequest):
        """Create stripe customer
        - name
        - email
        - address
            - line1: "Rua Augusta, 100"
            - city: "São Paulo"
            - state: "SP"
            - country: "BR"
            - postal_code: "01304-000"
        """
        try:
            body = loads(request.body)
            assert "name" in body
            assert "email" in body
            assert "address" in body

            account = Account.objects.get(id=body.account_id)
            customer = DJStripeCustomer.create(account)
            customer = StripeCustomer.modify(customer.id, **body)

            return JsonResponse(customer.values())
        except (JSONDecodeError, KeyError) as e:
            logger.error(e)
            return JsonResponse({}, status=400)
        except Exception as e:
            logger.error(e)
            return JsonResponse({"error": str(e)}, status=422)

    @csrf_exempt
    @login_required
    def put(self, request: HttpRequest, account_id: str):
        """Update stripe customer
        - name
        - email
        - address
            - line1: "Rua Augusta, 100"
            - city: "São Paulo"
            - state: "SP"
            - country: "BR"
            - postal_code: "01304-000"
        """
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


class StripeSubscriptionView(View):
    @csrf_exempt
    @login_required
    def post(self, request: HttpRequest):
        """Create stripe subscription"""
        try:
            body = loads(request.body)
            account = Account.objects.get(id=body.account_id)
            customer: DJStripeCustomer = account.djstripe_customers[0]
            subscription: DJStripeSubscription = customer.subscribe(
                price=body.price_id,
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

    @csrf_exempt
    @login_required
    def delete(self, request: HttpRequest, subscription_id: str):
        """Delete stripe subscription"""

        try:
            subscription = DJStripeSubscription.objects.get(id=subscription_id)
            subscription = subscription.cancel()
            return JsonResponse({})
        except Exception as e:
            logger.error(e)
            return JsonResponse({"error": str(e)}, status=422)


class StripeCustomerSubscriptionView(View):
    @csrf_exempt
    @login_required
    def post(self, request: HttpRequest, account_id: str, subscription_id: str):
        """Add customer to a stripe subscription"""
        ...

    @csrf_exempt
    @login_required
    def delete(self, request: HttpRequest, account_id: str, subscription_id: str):
        """Remove customer from a stripe subscription"""
        ...


# Reference
# https://stripe.com/docs/billing/subscriptions/build-subscriptions?ui=elementsf
