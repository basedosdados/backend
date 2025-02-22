# -*- coding: utf-8 -*-
import json
from decimal import Decimal
from hashlib import sha256

from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from backend.apps.api.v1.models import MeasurementUnit

from .decorators import cloud_function_only, stripe_webhook_only
from .models import Credit, Endpoint, Key, Request


class DataAPIKeyValidateView(View):
    def get(self, request):
        key = request.GET.get("key")
        if not key:
            return JsonResponse({"error": "API key not provided", "success": False}, status=400)

        # Hash the API key
        hashed_key = sha256(key.encode()).hexdigest()

        try:
            key = Key.objects.get(hash=hashed_key)

            # Check if key is expired
            is_expired = False
            if key.expires_at and key.expires_at < timezone.now():
                is_expired = True

            return JsonResponse(
                {
                    "success": True,
                    "resource": {
                        "isActive": key.is_active and not is_expired,
                        "createdAt": key.created_at,
                        "expiresAt": key.expires_at,
                        "balance": float(key.balance),
                    },
                }
            )
        except Key.DoesNotExist:
            return JsonResponse({"error": "API key not found", "success": False}, status=404)


class DataAPICurrentTierView(View):
    def get(self, request):
        key = request.GET.get("key")
        category_slug = request.GET.get("category")
        endpoint_slug = request.GET.get("endpoint")

        if not all([key, category_slug, endpoint_slug]):
            return JsonResponse(
                {"error": "Missing required parameters", "success": False}, status=400
            )

        # Hash the API key
        hashed_key = sha256(key.encode()).hexdigest()

        try:
            key = Key.objects.get(hash=hashed_key)
            endpoint = Endpoint.objects.get(category__slug=category_slug, slug=endpoint_slug)

            # Get the first day of current month
            today = timezone.now()
            first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Count requests for current month
            monthly_requests = Request.objects.filter(
                key=key, endpoint=endpoint, created_at__gte=first_day
            ).count()

            # Get current pricing tier
            current_tier = endpoint.get_pricing_tier(monthly_requests)

            if not current_tier:
                return JsonResponse(
                    {"error": "No pricing tier found for this request volume", "success": False},
                    status=404,
                )

            return JsonResponse(
                {
                    "success": True,
                    "resource": {
                        "monthly_requests": monthly_requests,
                        "current_tier": {
                            "min_requests": current_tier.min_requests,
                            "max_requests": current_tier.max_requests,
                            "price_per_request": float(current_tier.price_per_request),
                        },
                    },
                }
            )

        except Key.DoesNotExist:
            return JsonResponse({"error": "API key not found", "success": False}, status=404)
        except Endpoint.DoesNotExist:
            return JsonResponse({"error": "Endpoint not found", "success": False}, status=404)


@method_decorator(csrf_exempt, name="dispatch")
class DataAPICreditAddView(View):
    # TODO: remove GET method when in production
    def get(self, request):
        key = request.GET.get("key")
        amount = request.GET.get("amount")
        currency = request.GET.get("currency")

        if not all([key, amount, currency]):
            return JsonResponse(
                {"error": "Missing required parameters", "success": False}, status=400
            )

        # Validate currency is BRL
        if currency != "BRL":
            return JsonResponse(
                {"error": "Only BRL currency is supported", "success": False}, status=400
            )

        try:
            amount = float(amount)
        except ValueError:
            return JsonResponse({"error": "Invalid amount format", "success": False}, status=400)

        # Hash the API key
        hashed_key = sha256(key.encode()).hexdigest()

        try:
            amount = Decimal(str(amount))
            key = Key.objects.get(hash=hashed_key)
            currency_obj = MeasurementUnit.objects.get(slug=currency.lower())

            # Create credit record
            Credit.objects.create(key=key, amount=amount, currency=currency_obj)

            # Update API key balance
            key.balance += amount
            key.save()

            return JsonResponse({"success": True, "new_balance": float(key.balance)})

        except Key.DoesNotExist:
            return JsonResponse({"error": "API key not found", "success": False}, status=404)
        except MeasurementUnit.DoesNotExist:
            return JsonResponse({"error": "Currency not found", "success": False}, status=404)

    @stripe_webhook_only
    def post(self, request):
        event = request.stripe_event

        # Only process successful payment events
        if event.type != "payment_intent.succeeded":
            return JsonResponse({"success": True, "message": f"Ignored event type {event.type}"})

        try:
            payment_intent = event.data.object
            metadata = payment_intent.metadata

            key = metadata.get("key")
            amount = float(payment_intent.amount) / 100  # Convert from cents to BRL
            currency = payment_intent.currency.upper()

            if not key:
                raise ValueError("API key not found in payment metadata")

            # Hash the API key
            hashed_key = sha256(key.encode()).hexdigest()

            try:
                amount = Decimal(str(amount))
                key = Key.objects.get(hash=hashed_key)
                currency_obj = MeasurementUnit.objects.get(slug=currency.lower())

                # Create credit record
                Credit.objects.create(key=key, amount=amount, currency=currency_obj)

                # Update API key balance
                key.balance += amount
                key.save()

                return JsonResponse({"success": True, "new_balance": float(key.balance)})

            except Key.DoesNotExist:
                return JsonResponse({"error": "API key not found", "success": False}, status=404)
            except MeasurementUnit.DoesNotExist:
                return JsonResponse({"error": "Currency not found", "success": False}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e), "success": False}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class DataAPICreditDeductView(View):
    # TODO: remove GET method when in production
    def get(self, request):
        key = request.GET.get("key")
        amount = request.GET.get("amount")
        currency = request.GET.get("currency")

        if not all([key, amount, currency]):
            return JsonResponse(
                {"error": "Missing required parameters", "success": False}, status=400
            )

        # Validate currency is BRL
        if currency != "BRL":
            return JsonResponse(
                {"error": "Only BRL currency is supported", "success": False}, status=400
            )

        try:
            amount = float(amount)
        except ValueError:
            return JsonResponse({"error": "Invalid amount format", "success": False}, status=400)

        # Hash the API key
        hashed_key = sha256(key.encode()).hexdigest()

        try:
            amount = Decimal(str(amount))
            key = Key.objects.get(hash=hashed_key)
            currency = MeasurementUnit.objects.get(slug="brl")

            # Check if there's enough balance
            if key.balance < amount:
                return JsonResponse({"error": "Insufficient balance", "success": False}, status=400)

            # Update API key balance
            key.balance -= amount
            key.save()

            return JsonResponse({"success": True, "new_balance": float(key.balance)})

        except Key.DoesNotExist:
            return JsonResponse({"error": "API key not found", "success": False}, status=404)
        except MeasurementUnit.DoesNotExist:
            return JsonResponse({"error": "Currency not found", "success": False}, status=404)

    @cloud_function_only
    def post(self, request):
        event = request.stripe_event

        # Only process successful payment events
        if event.type != "payment_intent.succeeded":
            return JsonResponse({"success": True, "message": f"Ignored event type {event.type}"})

        try:
            payment_intent = event.data.object
            metadata = payment_intent.metadata

            key = metadata.get("key")
            amount = float(payment_intent.amount) / 100  # Convert from cents to currency units
            currency = payment_intent.currency.upper()

            if not key:
                raise ValueError("API key not found in payment metadata")

            # Hash the API key
            hashed_key = sha256(key.encode()).hexdigest()

            try:
                amount = Decimal(str(amount))
                key = Key.objects.get(hash=hashed_key)
                currency_obj = MeasurementUnit.objects.get(slug=currency.lower())

                # Create credit record
                Credit.objects.create(key=key, amount=amount, currency=currency_obj)

                # Update API key balance
                key.balance += amount
                key.save()

                return JsonResponse({"success": True, "new_balance": float(key.balance)})

            except Key.DoesNotExist:
                return JsonResponse({"error": "API key not found", "success": False}, status=404)
            except MeasurementUnit.DoesNotExist:
                return JsonResponse({"error": "Currency not found", "success": False}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e), "success": False}, status=400)


class DataAPIEndpointValidateView(View):
    def get(self, request):
        category_slug = request.GET.get("category")
        endpoint_slug = request.GET.get("endpoint")

        if not all([category_slug, endpoint_slug]):
            return JsonResponse(
                {"error": "Both category and endpoint slugs are required", "success": False},
                status=400,
            )

        try:
            endpoint = Endpoint.objects.get(category__slug=category_slug, slug=endpoint_slug)

            return JsonResponse(
                {
                    "success": True,
                    "resource": {
                        "isActive": endpoint.is_active and not endpoint.is_deprecated,
                        "isDeprecated": endpoint.is_deprecated,
                        "createdAt": endpoint.created_at,
                    },
                }
            )

        except Endpoint.DoesNotExist:
            return JsonResponse({"error": "Endpoint not found", "success": False}, status=404)


@method_decorator(csrf_exempt, name="dispatch")
class DataAPIRequestRegisterView(View):
    # TODO: remove GET method when in production
    def get(self, request):
        key = request.GET.get("key")
        category_slug = request.GET.get("category")
        endpoint_slug = request.GET.get("endpoint")
        parameters_str = request.GET.get("parameters", "")
        error_message = request.GET.get("error_message", "")
        response_time = request.GET.get("response_time", "0.0")  # Changed default to "0.0"
        bytes_processed = request.GET.get("bytes_processed", "0")

        if not all([key, category_slug, endpoint_slug]):
            return JsonResponse(
                {"error": "Missing required parameters", "success": False}, status=400
            )

        # Parse parameters from x:2,y:tfwas format to dict
        parameters = {}
        if parameters_str:
            try:
                for param in parameters_str.split(","):
                    if ":" in param:
                        k, v = param.split(":", 1)
                        parameters[k.strip()] = v.strip()
            except Exception:
                return JsonResponse(
                    {
                        "error": (
                            "Invalid parameters format. " "Use format: param1:value1,param2:value2"
                        ),
                        "success": False,
                    },
                    status=400,
                )

        # Hash the API key
        hashed_key = sha256(key.encode()).hexdigest()

        try:
            # Get API key and endpoint first
            key = Key.objects.get(hash=hashed_key)
            endpoint = Endpoint.objects.get(category__slug=category_slug, slug=endpoint_slug)

            # Get required parameters for this endpoint
            required_params = endpoint.parameters.filter(is_required=True).values_list(
                "name", flat=True
            )

            # Check if all required parameters are present
            missing_params = [param for param in required_params if param not in parameters]
            if missing_params:
                return JsonResponse(
                    {
                        "error": (
                            f"Missing required endpoint parameters: " f"{', '.join(missing_params)}"
                        ),
                        "success": False,
                    },
                    status=400,
                )

            # Convert numeric values after parameter validation
            try:
                response_time = float(response_time)
                bytes_processed = int(bytes_processed)
            except (ValueError, TypeError):
                return JsonResponse(
                    {
                        "error": "Invalid numeric values for response_time or bytes_processed",
                        "success": False,
                    },
                    status=400,
                )

            # Create request record
            Request.objects.create(
                key=key,
                endpoint=endpoint,
                parameters=parameters,
                error_message=error_message,
                response_time=response_time,
                bytes_processed=bytes_processed,
            )

            return JsonResponse({"success": True})

        except Key.DoesNotExist:
            return JsonResponse({"error": "API key not found", "success": False}, status=404)
        except Endpoint.DoesNotExist:
            return JsonResponse({"error": "Endpoint not found", "success": False}, status=404)

    @cloud_function_only
    def post(self, request):
        key = request.POST.get("key")
        category_slug = request.POST.get("category")
        endpoint_slug = request.POST.get("endpoint")
        parameters = request.POST.get("parameters", "{}")
        error_message = request.POST.get("error_message", "")
        response_time = request.POST.get("response_time", "0")
        bytes_processed = request.POST.get("bytes_processed", "0")

        if not all([key, category_slug, endpoint_slug, parameters]):
            return JsonResponse(
                {"error": "Missing required parameters", "success": False}, status=400
            )

        # Hash the API key
        hashed_key = sha256(key.encode()).hexdigest()

        try:
            # Convert parameters
            parameters = json.loads(parameters)
            response_time = float(response_time)
            bytes_processed = int(bytes_processed)

            # Get API key and endpoint
            key = Key.objects.get(hash=hashed_key)
            endpoint = Endpoint.objects.get(category__slug=category_slug, slug=endpoint_slug)

            # Get required parameters for this endpoint
            required_params = endpoint.parameters.filter(is_required=True).values_list(
                "name", flat=True
            )

            # Check if all required parameters are present
            missing_params = [param for param in required_params if param not in parameters]
            if missing_params:
                return JsonResponse(
                    {
                        "error": (
                            f"Missing required endpoint parameters: " f"{', '.join(missing_params)}"
                        ),
                        "success": False,
                    },
                    status=400,
                )

            # Create request record
            Request.objects.create(
                key=key,
                endpoint=endpoint,
                parameters=parameters,
                error_message=error_message,
                response_time=response_time,
                bytes_processed=bytes_processed,
            )

            return JsonResponse({"success": True})

        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid parameters JSON format", "success": False}, status=400
            )
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid numeric values", "success": False}, status=400)
        except Key.DoesNotExist:
            return JsonResponse({"error": "API key not found", "success": False}, status=404)
        except Endpoint.DoesNotExist:
            return JsonResponse({"error": "Endpoint not found", "success": False}, status=404)
