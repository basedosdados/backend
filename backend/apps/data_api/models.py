# -*- coding: utf-8 -*-
from hashlib import sha256
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models

from backend.apps.account.models import Account
from backend.apps.api.v1.models import BigQueryType, Column, Dataset, MeasurementUnit, Table
from backend.custom.model import BaseModel


class Key(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="keys")
    name = models.CharField(
        max_length=100, null=True, blank=True, help_text="A friendly name to identify this key"
    )
    hash = models.CharField(
        max_length=64, unique=True, null=True, blank=True, help_text="The hashed key"
    )
    prefix = models.CharField(
        max_length=8,
        unique=True,
        null=True,
        blank=True,
        help_text="First 8 characters of the key",
    )
    is_active = models.BooleanField(default=True)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="The balance of the key in BRL",
    )
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Key"
        verbose_name_plural = "Keys"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def create_key(cls, **kwargs):
        key = str(uuid4())
        obj = cls(**kwargs)
        obj.prefix = key[:8]
        obj.hash = sha256(key.encode()).hexdigest()
        obj.save()
        return obj, key


class EndpointCategory(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(max_length=100)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        related_name="endpoint_categories",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Endpoint Category"
        verbose_name_plural = "Endpoint Categories"
        ordering = ["created_at"]

    def __str__(self):
        return self.name


class Endpoint(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(max_length=100)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        related_name="endpoints",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        EndpointCategory,
        on_delete=models.SET_NULL,
        related_name="endpoints",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_deprecated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Endpoint"
        verbose_name_plural = "Endpoints"
        ordering = ["created_at"]

    def __str__(self):
        return self.name

    @property
    def full_name(self):
        return f"{self.category.name}.{self.name}"

    @property
    def full_slug(self):
        return f"{self.category.slug}.{self.slug}"

    @property
    def parameters(self):
        return self.parameters.all()

    def clean(self):
        super().clean()
        # TODO: Add validation for pricing tiers to ensure:
        # 1. No overlapping tiers
        # 2. No gaps between tiers
        # 3. Only one unlimited tier
        # Note: Consider implementing this at the form/admin level to allow individual tier edits

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_pricing_tier(self, request_count: int):
        """
        Get the pricing tier for a given number of requests.

        Args:
            request_count (int): Number of requests made in the current period

        Returns:
            EndpointPricingTier: The pricing tier object that matches the request count,
                                or None if no matching tier is found
        """
        return self.pricing_tiers.filter(
            models.Q(min_requests__lte=request_count)
            & (models.Q(max_requests__gte=request_count) | models.Q(max_requests__isnull=True))
        ).first()


class EndpointParameter(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    type = models.ForeignKey(
        BigQueryType,
        on_delete=models.SET_NULL,
        related_name="parameters",
        null=True,
        blank=True,
    )
    is_required = models.BooleanField(default=False)
    endpoint = models.ForeignKey(
        Endpoint,
        on_delete=models.SET_NULL,
        related_name="parameters",
        null=True,
        blank=True,
    )
    column = models.ForeignKey(
        Column,
        on_delete=models.SET_NULL,
        related_name="parameters",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Endpoint Parameter"
        verbose_name_plural = "Endpoint Parameters"

    def __str__(self):
        return f"{self.endpoint.name} - {self.name}"


class Request(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    key = models.ForeignKey(Key, on_delete=models.DO_NOTHING, related_name="requests")
    endpoint = models.ForeignKey(Endpoint, on_delete=models.DO_NOTHING, related_name="requests")
    parameters = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    response_time = models.FloatField(default=0)
    bytes_processed = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Request"
        verbose_name_plural = "Requests"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.key.name} - {self.endpoint.name}"


class Credit(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    key = models.ForeignKey(Key, on_delete=models.DO_NOTHING, related_name="credits")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01, message="Amount must be greater than zero")],
    )
    currency = models.ForeignKey(
        MeasurementUnit,
        on_delete=models.SET_NULL,
        related_name="credits",
        limit_choices_to={"category__slug": "currency"},
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Credit"
        verbose_name_plural = "Credits"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.key.name} - {self.amount} {self.currency.name}"


class EndpointPricingTier(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name="pricing_tiers")
    min_requests = models.PositiveIntegerField(help_text="Minimum number of requests for this tier")
    max_requests = models.PositiveIntegerField(
        help_text="Maximum number of requests for this tier", null=True, blank=True
    )
    price_per_request = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Price per request",
        validators=[MinValueValidator(0)],
    )
    currency = models.ForeignKey(
        MeasurementUnit,
        on_delete=models.SET_NULL,
        related_name="endpoint_pricing_tiers",
        limit_choices_to={"category__slug": "currency"},
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Endpoint Pricing Tier"
        verbose_name_plural = "Endpoint Pricing Tiers"
        ordering = ["min_requests"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_requests__gt=models.F("min_requests"))
                | models.Q(max_requests__isnull=True),
                name="max_requests_greater_than_min",
            )
        ]

    def __str__(self):
        if self.max_requests:
            return (
                f"{self.endpoint.name}: {self.min_requests}-{self.max_requests} "
                f"requests @ R${self.price_per_request}"
            )
        return f"{self.endpoint.name}: {self.min_requests}+ requests @ R${self.price_per_request}"
