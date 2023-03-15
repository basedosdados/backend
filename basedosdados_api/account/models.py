# -*- coding: utf-8 -*-
from uuid import uuid4

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
    Permission,
)

from basedosdados_api.custom.model import BdmModel


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
    username = models.CharField(
        "Username", max_length=40, blank=True, null=True, unique=True
    )

    first_name = models.CharField("Nome", max_length=40, blank=True)
    last_name = models.CharField("Sobrenome", max_length=40, blank=True)
    birth_date = models.DateField("Data de Nascimento", null=True, blank=True)
    picture = models.ImageField(
        "Imagem", upload_to="profile_pictures", null=True, blank=True
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

    groups = models.ManyToManyField(
        BDGroup,
        related_name="users",
        verbose_name="Grupos",
        related_query_name="user",
        blank=True,
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
