# -*- coding: utf-8 -*-
from uuid import uuid4

from django.db import models
from django.contrib.auth.models import User

from basedosdados_api.api.v1.models import Organization


class RegistrationToken(models.Model):
    token = models.CharField(max_length=255, unique=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.token

    class Meta:
        verbose_name = "Registration Token"
        verbose_name_plural = "Registration Tokens"


class Profile(models.Model):
    # Foreign
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organizations = models.ManyToManyField(
        Organization, related_name="users", blank=True
    )
    # Mandatory
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255)
    # Optional
    birth_date = models.DateField(null=True, blank=True)
    picture_url = models.URLField(null=True, blank=True)
    twitter = models.CharField(max_length=255, null=True, blank=True)
    linkedin = models.CharField(max_length=255, null=True, blank=True)
