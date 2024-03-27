# -*- coding: utf-8 -*-
from uuid import uuid4

from django.conf import settings
from django.db import models

USER_MODEL = settings.AUTH_USER_MODEL


class Domain(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Token(models.Model):
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, related_name="tokens")
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="tokens")
    token = models.CharField(max_length=255, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.domain} - {self.token}"

    def generate_token(self):
        return str(uuid4())

    def save(self):
        self.token = self.generate_token()
        super().save()


class Access(models.Model):
    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    token = models.ForeignKey(
        Token, on_delete=models.CASCADE, related_name="accesses", null=True, blank=True
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="accesses",
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField()

    def __str__(self):
        return (
            f"{self.timestamp} - {'OK' if self.success else 'ERR'} - "
            f"{self.domain if self.domain else 'NO_DOMAIN'} - "
            f"{self.token.user.username if self.token else 'NO_TOKEN'}"
        )
