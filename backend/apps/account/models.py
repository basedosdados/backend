# -*- coding: utf-8 -*-
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
from django.db.models.query import QuerySet
from django.utils import timezone

from backend.apps.account.enums import (
    AvailableForResearch,
    DiscoveryMethod,
    WorkArea,
    WorkDataTool,
    WorkGoal,
    WorkRole,
    WorkSize,
)
from backend.custom.graphql_jwt import owner_required, subscription_member
from backend.custom.model import BaseModel
from backend.custom.storage import OverwriteStorage, upload_to, validate_image


class RegistrationToken(BaseModel):
    token = models.CharField(max_length=255, unique=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.token

    graphql_visible = False

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


class BDRole(BaseModel):
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


class BDGroup(BaseModel):
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


class BDGroupRole(BaseModel):
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
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)

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
        account.is_active = True
        account.save()
        return account


class Account(BaseModel, AbstractBaseUser, PermissionsMixin):
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
    gcp_email = models.EmailField("GCP email", null=True, blank=True)  # Google Cloud Platform email
    username = models.CharField("Username", max_length=40, blank=True, null=True, unique=True)

    first_name = models.CharField("Nome", max_length=40, blank=True)
    last_name = models.CharField("Sobrenome", max_length=40, blank=True)
    full_name = models.CharField("Nome Completo", max_length=100, blank=True, null=True)
    birth_date = models.DateField("Data de Nascimento", null=True, blank=True)
    picture = models.ImageField(
        "Imagem",
        null=True,
        blank=True,
        storage=OverwriteStorage(),
        upload_to=upload_to,
        validators=[validate_image],
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
    is_email_visible = models.BooleanField(
        "Email é visível", default=False, help_text="Indica se o email do usuário é público"
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
    deleted_at = models.DateTimeField(null=True, blank=True)

    # UX Research <
    work_area = models.TextField(
        null=True,
        blank=True,
        choices=WorkArea.as_choices(),
        verbose_name="Área",
    )
    work_role = models.TextField(
        null=True,
        blank=True,
        choices=WorkRole.as_choices(),
        verbose_name="Cargo",
    )
    work_size = models.TextField(
        null=True,
        blank=True,
        choices=WorkSize.as_choices(),
        verbose_name="Tamanho da empresa",
    )
    work_goal = models.TextField(
        null=True,
        blank=True,
        choices=WorkGoal.as_choices(),
        verbose_name="Objetivo com a ONG",
    )
    work_data_tool = models.TextField(
        null=True,
        blank=True,
        choices=WorkDataTool.as_choices(),
        verbose_name="Ferramenta principal de análise de dados",
    )
    discovery_method = models.TextField(
        null=True,
        blank=True,
        choices=DiscoveryMethod.as_choices(),
        verbose_name="Como conheceu a ONG",
    )
    available_for_research = models.TextField(
        null=True,
        blank=True,
        choices=AvailableForResearch.as_choices(),
        verbose_name="Se gostaria de participar de pesquisas",
    )
    # UX Research >

    objects = AccountManager()

    graphql_fields_blacklist = [
        "is_admin",
        "is_superuser",
        "staff_groups",
        *BaseModel.graphql_fields_blacklist,
    ]
    graphql_filter_fields_blacklist = ["internal_subscription"]
    graphql_nested_filter_fields_whitelist = ["email", "username"]
    graphql_query_decorator = owner_required(allow_anonymous=False)
    graphql_mutation_decorator = owner_required(allow_anonymous=True)

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

    @property
    def is_subscriber(self) -> bool:
        return bool(self.pro_subscription)

    @property
    def customer(self):
        return self.djstripe_customers.first()

    @property
    def pro_owner_subscription(self):
        sub = self.internal_subscription.filter(is_active=True).all() or []
        sub = [s for s in sub if s.is_pro]
        return sub[0] if sub else None

    @property
    def pro_member_subscription(self):
        sub = self.subscription_set.filter(is_active=True).all() or []
        sub = [s for s in sub if s.is_pro]
        return sub[0] if sub else None

    @property
    def pro_subscription(self) -> str:
        """BD Pro subscription role, one of bd_pro or bd_pro_empresas"""
        if self.pro_owner_subscription:
            return self.pro_owner_subscription.stripe_subscription
        if self.pro_member_subscription:
            return self.pro_member_subscription.stripe_subscription

    @property
    def pro_subscription_role(self) -> str:
        """BD Pro subscription role, one of owner or member"""
        if self.pro_owner_subscription:
            return "owner"
        if self.pro_member_subscription:
            return "member"

    @property
    def pro_subscription_slots(self) -> str:
        """BD Pro subscription slots"""
        if self.pro_owner_subscription:
            return self.pro_owner_subscription.stripe_subscription_slots
        if self.pro_member_subscription:
            return self.pro_member_subscription.stripe_subscription_slots

    @property
    def pro_subscription_status(self) -> str:
        def convert_status(status: str) -> str:
            if status == "trialing":
                return "active"
            return status

        """BD Pro subscription status"""
        if self.pro_owner_subscription:
            return convert_status(self.pro_owner_subscription.stripe_subscription_status)
        if self.pro_member_subscription:
            return convert_status(self.pro_member_subscription.stripe_subscription_status)

    def __str__(self):
        return self.email

    def get_short_name(self):
        return self.first_name

    get_short_name.short_description = "nome"

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.username

    get_full_name.short_description = "nome completo"

    def get_organization(self):
        return ", ".join(self.organizations.all().values_list("name", flat=True))

    get_organization.short_description = "organização"

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

    def delete(self):
        self.deleted_at = timezone.now()
        self.save()


class Team(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField("Name", max_length=100, unique=True)
    description = models.TextField("Description", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Role(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField("Name", max_length=100, unique=True)
    description = models.TextField("Description", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Career(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    account = models.ForeignKey(Account, on_delete=models.DO_NOTHING, related_name="careers")
    team_old = models.CharField("Team (old)", max_length=40, blank=True)
    team = models.ForeignKey(
        Team, on_delete=models.DO_NOTHING, related_name="careers", null=True, blank=True
    )
    role_old = models.CharField("Role (old)", max_length=40, blank=True)
    role = models.ForeignKey(
        Role, on_delete=models.DO_NOTHING, related_name="careers", null=True, blank=True
    )
    level = models.CharField("Level", max_length=40, blank=True)
    start_at = models.DateField("Start at", null=True, blank=True)
    end_at = models.DateField("End at", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Career"
        verbose_name_plural = "Careers"

    def __str__(self):
        return f"{self.account.email} @{self.role.name}" if self.role else ""

    def get_team(self):
        return self.team.name if self.team else ""

    get_team.short_description = "Team"


class Subscription(BaseModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    id = models.UUIDField(primary_key=True, default=uuid4)

    is_active = models.BooleanField(
        "Ativo",
        default=False,
        help_text="Indica se a inscrição está ativa",
    )

    admin = models.ForeignKey(
        "Account",
        on_delete=models.DO_NOTHING,
        related_name="internal_subscription",
    )
    subscription = models.OneToOneField(
        "djstripe.Subscription",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        related_name="internal_subscription",
    )
    subscribers = models.ManyToManyField(Account)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.admin.email} @ {self.subscription.plan}"

    graphql_query_decorator = subscription_member(only_admin=False)
    graphql_mutation_decorator = subscription_member(only_admin=True)

    @property
    def admin_email(self):
        return self.admin.email or "test@stripe.com"

    @property
    def subscribers_info(self) -> list[dict]:
        info = [
            {
                "email": self.admin.email,
                "role": "admin",
            }
        ]
        for subscriber in self.subscribers.all():
            info.append(
                {
                    "email": subscriber.email,
                    "role": "subscriber",
                }
            )
        return info

    @property
    def stripe_subscription(self):
        return self.subscription.plan.product.metadata.get("code", "")

    @property
    def stripe_subscription_slots(self):
        return self.subscription.plan.product.metadata.get("slots", "0")

    @property
    def stripe_subscription_status(self):
        return self.subscription.status.lower().replace(" ", "_")

    @property
    def stripe_subscription_created_at(self):
        return self.subscription.created

    @property
    def is_pro(self):
        return "bd_pro" in self.subscription.plan.product.metadata.get("code", "")

    @property
    def canceled_at(self):
        if self.subscription:
            return self.subscription.cancel_at.isoformat()
        return None

    @property
    def plan_interval(self):
        if self.subscription:
            return self.subscription.plan.interval
        return None

    @property
    def next_billing_cycle(self):
        if self.subscription:
            return self.subscription.current_period_end.isoformat()
        return None


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
