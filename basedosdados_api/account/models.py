# -*- coding: utf-8 -*-
from uuid import uuid4

from django.db import models

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


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


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, profile=2, **kwargs):
        if not email:
            raise ValueError("Users must have a valid email address.")

        if not kwargs.get("username"):
            raise ValueError("Users must have a valid username.")

        account = self.model(
            email=self.normalize_email(email),
            username=kwargs.get("username"),
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
            profile=profile,
            is_superuser=False,
        )

        account.set_password(password)
        account.save()

        return account

    def create_superuser(self, email, password, **kwargs):

        account = self.create_user(email, password, profile=1, **kwargs)

        account.is_admin = True
        account.is_superuser = True
        account.save()

        return account


class Account(AbstractBaseUser, PermissionsMixin):
    STAFF = 1
    VISITANTE = 2
    COLABORADOR = 3

    PROFILE_CHOICES = (
        (STAFF, "Staff"),
        (VISITANTE, "Visitante"),
        (COLABORADOR, "Colaborador"),
    )

    email = models.EmailField("Email", unique=True)
    username = models.CharField("Username", max_length=40, unique=True)

    first_name = models.CharField("Nome", max_length=40, blank=True)
    last_name = models.CharField("Sobrenome", max_length=40, blank=True)
    birth_date = models.DateField("Data de Nascimento", null=True, blank=True)
    picture = models.ImageField("Imagem", upload_to="profile_pictures", null=True, blank=True)
    twitter = models.CharField("Twitter", max_length=255, null=True, blank=True)
    linkedin = models.CharField("Linkedin", max_length=255, null=True, blank=True)
    github = models.CharField("Github", max_length=255, null=True, blank=True)
    website = models.URLField("Website", null=True, blank=True)
    description = models.TextField("Descrição", null=True, blank=True)

    organizations = models.ManyToManyField(
        "v1.Organization", related_name="users", blank=True
    )

    is_admin = models.BooleanField(
        "Membro da equipe",
        default=False,
        help_text="Indica se tem acesso à administração",
    )
    is_active = models.BooleanField(
        "Ativo", default=True, help_text="Indica se o usuário está ativo"
    )

    profile = models.IntegerField(
        choices=PROFILE_CHOICES,
        default=VISITANTE,
        verbose_name="Perfil",
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
        ordering = ["first_name", "last_name"]

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

    def get_organization(self):
        return ", ".join(self.organizations.all().values_list("name", flat=True))

    get_organization.short_description = "organização"

    def get_short_name(self):
        return self.first_name

    @property
    def is_staff(self):
        return self.is_admin
