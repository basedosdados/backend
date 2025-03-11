# -*- coding: utf-8 -*-
import os
from functools import wraps

import stripe
from django.http import JsonResponse


def cloud_function_only(view_func):
    @wraps(view_func)
    def wrapped_view(view_instance, request, *args, **kwargs):
        # Get the Cloud Function's secret key from environment variables
        cloud_function_key = os.getenv("DATA_API_CLOUD_FUNCTION")

        # Get the authorization header
        auth_header = request.headers.get("X-Data-API-Cloud-Function")

        if not auth_header or auth_header != cloud_function_key:
            return JsonResponse({"error": "Unauthorized access", "success": False}, status=403)

        return view_func(view_instance, request, *args, **kwargs)

    return wrapped_view


def stripe_webhook_only(view_func):
    @wraps(view_func)
    def wrapped_view(view_instance, request, *args, **kwargs):
        # Get the Stripe webhook secret from environment variables
        stripe_webhook_secret = os.getenv("DATA_API_STRIPE_WEBHOOK")

        # Get the Stripe signature header
        stripe_signature = request.headers.get("X-Data-API-Stripe-Signature")

        if not stripe_signature:
            return JsonResponse({"error": "Missing Stripe signature", "success": False}, status=403)

        try:
            # Verify the event using the signature and webhook secret
            event = stripe.Webhook.construct_event(
                request.body, stripe_signature, stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            return JsonResponse({"error": "Invalid Stripe signature", "success": False}, status=403)
        except Exception:
            return JsonResponse({"error": "Invalid webhook request", "success": False}, status=400)

        # Add the verified Stripe event to the request
        request.stripe_event = event

        return view_func(view_instance, request, *args, **kwargs)

    return wrapped_view
