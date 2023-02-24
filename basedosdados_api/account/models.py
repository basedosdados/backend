# -*- coding: utf-8 -*-
from uuid import uuid4

from django.db import models
# from django.contrib.auth.models import User

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.conf import settings

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


# class Profile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     organizations = models.ManyToManyField(
#         Organization, related_name="users", blank=True
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     name = models.CharField(max_length=255)
#     description = models.TextField(null=True, blank=True)
#     birth_date = models.DateField(null=True, blank=True)
#     picture_url = models.URLField(null=True, blank=True)
#     twitter = models.CharField(max_length=255, null=True, blank=True)
#     linkedin = models.CharField(max_length=255, null=True, blank=True)
#     github = models.CharField(max_length=255, null=True, blank=True)
#     website = models.URLField(null=True, blank=True)
#     email = models.EmailField(null=True, blank=True)
#     # picture = models.ImageField(upload_to="profile_pictures", null=True, blank=True)

#     def __str__(self):
#         return self.name

#     class Meta:
#         db_table = "profile"
#         verbose_name = "Profile"
#         verbose_name_plural = "Profiles"
#         ordering = ["name"]


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, profile_id=2, **kwargs):
        if not email:
            raise ValueError("Users must have a valid email address.")

        if not kwargs.get("username"):
            raise ValueError("Users must have a valid username.")

        account = self.model(
            email=self.normalize_email(email),
            username=kwargs.get("username"),
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
            profile_id=profile_id,
            is_superuser=False,
        )

        account.set_password(password)
        account.save()

        return account

    def create_superuser(self, email, password, **kwargs):

        account = self.create_user(email, password, profile_id=1, **kwargs)

        account.is_admin = True
        account.is_superuser = True
        account.save()

        return account


class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=40, unique=True)

    first_name = models.CharField(max_length=40, blank=True)
    last_name = models.CharField(max_length=40, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    # picture    = models.ImageField(upload_to="profile_pictures", null=True, blank=True)
    twitter = models.CharField(max_length=255, null=True, blank=True)
    linkedin = models.CharField(max_length=255, null=True, blank=True)
    github = models.CharField(max_length=255, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)


    is_admin = models.BooleanField(
        "Membro da equipe",
        default=False,
        help_text="Indica se tem acesso à administração",
    )
    is_active = models.BooleanField(
        "Ativo", default=True, help_text="Indica se o usuário está ativo"
    )

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, verbose_name="Perfil"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        db_table = "account"
        verbose_name = "account" 
        verbose_name_plural = "accounts"
        ordering = ["get_full_name"]

    # def has_perm(self, perm, obj=None):
    #     return True
    #
    # def has_module_perms(self, app_label):
    #     return True

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    get_full_name.short_description = "nome completo"

    def get_company(self):
        return self.usercompany.company.name

    get_company.short_description = "empresa"

    def get_short_name(self):
        return self.first_name

    @property
    def is_staff(self):
        return self.is_admin
