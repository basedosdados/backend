# -*- coding: utf-8 -*-
import os
from typing import Tuple
from uuid import uuid4

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    Permission,
    PermissionsMixin,
)
from django.db import models

from bd_api.apps.account.storage import OverwriteStorage
from bd_api.apps.api.v1.validators import validate_is_valid_image_format
from bd_api.custom.model import BdmModel


def image_path_and_rename(instance, filename):
    """Rename file to be the username"""
    upload_to = instance.__class__.__name__.lower()
    ext = filename.split(".")[-1]
    filename = f"{instance.username}.{ext}"
    return os.path.join(upload_to, filename)


def split_password(password: str) -> Tuple[str, str, str, str]:
    """Split a password into four parts: algorithm, iterations, salt, and hash"""
    algorithm, iterations, salt, hash = password.split("$", 3)
    return algorithm, iterations, salt, hash


def is_valid_encoded_password(password: str) -> bool:
    """Check if a password is valid"""
    double_encoded = make_password(password)
    try:
        target_algorithm, target_iterations, _, _ = split_password(double_encoded)
        algorithm, iterations, _, _ = split_password(password)
    except ValueError:
        return False
    return algorithm == target_algorithm and iterations == target_iterations


class RegistrationToken(BdmModel):
    token = models.CharField(max_length=255, unique=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.token

    class Meta:
        verbose_name = "Registration Token"
        verbose_name_plural = "Registration Tokens"


class BDRoleManager(models.Manager):
    """
    The manager for the BD Role model.
    """

    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)


class BDRole(BdmModel):
    """
    Roles is a way to group permissions. Based on roles from IAM,
    a role is a collection of permissions that can be assigned to a group.
    A role can be assigned to multiple groups and a group can have multiple roles.
    It does not have a user field because it is not meant to be assigned to a user,
    and does not hold credentials, as these belong to the user.
    The relationship between roles and groups is defined in the BDGroupRole model,
    which also holds the organization to which the role is related.
    """

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        verbose_name="Permissions",
        related_query_name="role",
        blank=True,
    )

    graphql_nested_filter_fields_whitelist = ["name"]

    objects = BDRoleManager()

    class Meta:
        verbose_name = "BD role"
        verbose_name_plural = "BD roles"

    def __str__(self):
        return self.name


class BDGroupManager(models.Manager):
    """
    The manager for the BD Group model.
    """

    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)


class BDGroup(BdmModel):
    """
    Based on Group model from django.contrib.auth.models
    To avoid clashes with django.contrib.auth.models.Group
    we use BDGroup instead of Group. Users can be assigned
    to multiple groups and groups can have multiple roles,
    each one with a set of permissions. They must also be
    related to an organization, as an user can be part of
    multiple organizations with different roles and
    permissions. We use the through model BDGroupRole to
    link groups to roles.

    """

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    roles = models.ManyToManyField(
        BDRole,
        through="BDGroupRole",
        related_name="groups",
        verbose_name="Roles",
        related_query_name="group",
        blank=True,
    )

    objects = BDGroupManager()

    graphql_nested_filter_fields_whitelist = ["name"]

    class Meta:
        verbose_name = "BD group"
        verbose_name_plural = "BD groups"

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class BDGroupRole(BdmModel):
    """
    The model that links groups to roles.
    """

    group = models.ForeignKey(BDGroup, on_delete=models.CASCADE)
    role = models.ForeignKey(BDRole, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        "v1.Organization",
        on_delete=models.PROTECT,
        related_name="group_roles",
        related_query_name="group_role",
    )

    class Meta:
        verbose_name = "BD group role"
        verbose_name_plural = "BD group roles"
        constraints = [
            models.UniqueConstraint(
                fields=["group", "role", "organization"],
                name="unique_group_role_organization",
            )
        ]

    def __str__(self):
        return f"{self.group.name} - {self.role.name}"


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


class Account(BdmModel, AbstractBaseUser, PermissionsMixin):
    STAFF = 1
    VISITANTE = 2
    COLABORADOR = 3

    PROFILE_CHOICES = (
        (STAFF, "Staff"),
        (VISITANTE, "Visitante"),
        (COLABORADOR, "Colaborador"),
    )

    uuid = models.UUIDField(primary_key=False, default=uuid4)

    email = models.EmailField("Email", unique=True)
    username = models.CharField("Username", max_length=40, blank=True, null=True, unique=True)

    first_name = models.CharField("Nome", max_length=40, blank=True)
    last_name = models.CharField("Sobrenome", max_length=40, blank=True)
    full_name = models.CharField("Nome Completo", max_length=100, blank=True, null=True)
    birth_date = models.DateField("Data de Nascimento", null=True, blank=True)
    picture = models.ImageField(
        "Imagem",
        upload_to=image_path_and_rename,
        null=True,
        blank=True,
        validators=[validate_is_valid_image_format],
        storage=OverwriteStorage(),
    )
    twitter = models.CharField("Twitter", max_length=255, null=True, blank=True)
    linkedin = models.CharField("Linkedin", max_length=255, null=True, blank=True)
    github = models.CharField("Github", max_length=255, null=True, blank=True)
    website = models.URLField("Website", null=True, blank=True)
    description = models.TextField("Descrição", null=True, blank=True)

    organizations = models.ManyToManyField(
        "v1.Organization",
        related_name="users",
        verbose_name="Organizações",
        related_query_name="user",
        blank=True,
    )

    is_admin = models.BooleanField(
        "Admin",
        default=False,
        help_text="Indica se tem acesso à administração",
    )
    is_active = models.BooleanField(
        "Ativo", default=False, help_text="Indica se o usuário está ativo"
    )

    profile = models.IntegerField(
        choices=PROFILE_CHOICES,
        default=VISITANTE,
        verbose_name="Perfil",
    )

    groups = models.ManyToManyField(
        BDGroup,
        related_name="users",
        verbose_name="Grupos Externos",
        related_query_name="user",
        blank=True,
        help_text="Grupos de acesso ao app externo da BD",
    )

    staff_groups = models.ManyToManyField(
        Group,
        related_name="users",
        verbose_name="Grupos Internos",
        related_query_name="user",
        blank=True,
        help_text="Grupos de acesso ao admin",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountManager()

    graphql_nested_filter_fields_whitelist = ["email", "username"]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        db_table = "account"
        verbose_name = "account"
        verbose_name_plural = "accounts"
        ordering = ["first_name", "last_name"]

    @property
    def is_staff(self):
        return self.is_admin

    def __str__(self):
        return self.email

    def get_short_name(self):
        return self.first_name

    get_short_name.short_description = "nome"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    get_full_name.short_description = "nome completo"

    def get_organization(self):
        return ", ".join(self.organizations.all().values_list("name", flat=True))

    get_organization.short_description = "organização"

    def get_graphql_current_subscription(self):
        """Current stripe active subscription product"""
        try:
            subscription = self.subscription_set.filter(is_active=True).first()
            return subscription.stripe_subscription
        except Exception:
            return ""

    def get_graphql_current_subscription_status(self):
        """Current stripe active subscription status:
        - Incomplete, Incomplete Expired, Trialing, Active, Past Due, Canceled, Unpaid
        """
        try:
            subscription = self.subscription_set.filter(is_active=True).first()
            return subscription.stripe_subscription_status
        except Exception:
            return ""

    def save(self, *args, **kwargs) -> None:
        # If self._password is set and check_password(self._password, self.password) is True, then
        # just save the model without changing the password.
        if self._password and check_password(self._password, self.password):
            super().save(*args, **kwargs)
            return
        # If self._password is not set, we're probably not trying to modify the password, so if
        # self.password is valid, just save the model without changing the password.
        elif is_valid_encoded_password(self.password):
            super().save(*args, **kwargs)
            return
        # If self.password is not usable, then we're probably trying to set self.password as the
        # new password, so set it and save the model.
        self.set_password(self.password)
        super().save(*args, **kwargs)


class Career(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    account = models.ForeignKey(Account, on_delete=models.DO_NOTHING, related_name="careers")

    team = models.CharField("Equipe", max_length=40, blank=True)
    role = models.CharField("Cargo", max_length=40, blank=True)
    level = models.CharField("Nível", max_length=40, blank=True)

    start_at = models.DateField("Data de Início", null=True, blank=True)
    end_at = models.DateField("Data de Término", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Career"
        verbose_name_plural = "Careers"

    def __str__(self):
        return f"{self.account.first_name} @{self.role}"

    def get_team(self):
        return self.team

    get_team.short_description = "Equipe"


class Subscription(BdmModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    id = models.UUIDField(primary_key=True, default=uuid4)
    is_active = models.BooleanField(
        "Ativo",
        default=False,
        help_text="Indica se a inscrição está ativa",
    )

    admin = models.OneToOneField(
        "Account",
        on_delete=models.DO_NOTHING,
        related_name="admin_subscription",
    )
    subscribers = models.ManyToManyField(Account)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    @property
    def admin_name(self):
        return f"{self.admin.first_name} {self.admin.last_name}"

    @property
    def stripe_subscription(self):
        try:
            customer = self.admin.djstripe_customers.first()
            return customer.subscription.plan.product.name
        except Exception:
            return ""

    @property
    def stripe_subscription_status(self):
        try:
            customer = self.admin.djstripe_customers.first()
            return customer.subscription.status
        except Exception:
            return ""
