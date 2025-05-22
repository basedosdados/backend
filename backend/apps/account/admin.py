# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin as BaseAccountAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy
from faker import Faker

from backend.apps.account.models import Account, BDGroup, BDRole, Team, Role, Career, Subscription, DataAPIKey
from backend.apps.account.tasks import sync_subscription_task


def sync_subscription(modeladmin: ModelAdmin, request: HttpRequest, queryset: QuerySet):
    """Create internal subscriptions from stripe subscriptions"""
    sync_subscription_task()


sync_subscription.short_description = "Sincronizar inscrições"


class AccountCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(render_value=True),
        required=False,
    )
    password2 = forms.CharField(
        label="Confirme a senha",
        widget=forms.PasswordInput(render_value=True),
        required=False,
    )
    is_active = forms.BooleanField(
        label="Está ativo?",
        initial=True,
        required=False,
        help_text="Marque ativo para não enviar email de confirmação",
    )

    class Meta:
        model = Account
        fields = ("first_name", "last_name", "email", "username", "profile", "is_active")

    def clean_password2(self):
        """Check if the two password entries match"""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        """Save the provided password in hashed format"""
        user = super().save(commit=False)
        if not self.cleaned_data["password1"]:
            faker = Faker()
            user.set_password(faker.password())
        if self.cleaned_data["password1"]:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AccountChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """

    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Senha em formato hash. Não é possível visualizar a senha, mas você "
        "pode alterá-la usando '<a href=\"{}\">este formulário</a>.'",
    )

    class Meta:
        model = Account
        fields = (
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "full_name",
            "birth_date",
            "picture",
            "twitter",
            "linkedin",
            "github",
            "website",
            "description",
            "profile",
            "is_active",
            "is_admin",
            "is_superuser",
            "organizations",
        )

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password = self.fields.get("password")
        if password:
            password.help_text = password.help_text.format("../password/")
        user_permissions = self.fields.get("user_permissions")
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related("content_type")


class CareerInline(admin.StackedInline):
    model = Career
    extra = 0
    ordering = ["-start_at"]


class SubscriptionInline(admin.StackedInline):
    model = Subscription
    extra = 0
    ordering = ["-subscription__created"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SuperUserListFilter(admin.SimpleListFilter):
    title = gettext_lazy("Admin²")
    parameter_name = "superuser"

    def lookups(self, request, model_admin):
        return [
            ("true", gettext_lazy("Sim")),
            ("false", gettext_lazy("Não")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "true":
            return queryset.filter(is_superuser=True)
        if self.value() == "false":
            return queryset.filter(is_superuser=False)


class SubscriptionListFilter(admin.SimpleListFilter):
    title = gettext_lazy("Inscrito")
    parameter_name = "subscriber"

    def lookups(self, request, model_admin):
        return [
            ("true", gettext_lazy("Sim")),
            ("false", gettext_lazy("Não")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "true":
            return queryset.filter(internal_subscription__is_active=True)
        if self.value() == "false":
            return queryset.filter(internal_subscription__is_active=False)


class SubscriptionStatusListFilter(admin.SimpleListFilter):
    title = gettext_lazy("Tipo")
    parameter_name = "subscriber"

    def lookups(self, request, model_admin):
        return [
            ("trialing", gettext_lazy("Trial")),
            ("active", gettext_lazy("Active")),
            ("past_due", gettext_lazy("PastDue")),
            ("canceled", gettext_lazy("Canceled")),
            ("incomplete_expired", gettext_lazy("IncompleteExpired")),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(subscription__status=self.value())


class DataAPIKeyInline(admin.TabularInline):
    model = DataAPIKey
    extra = 0
    readonly_fields = (
        "id",
        "name",
        "prefix",
        "is_active",
        "expires_at",
        "last_used_at",
        "created_at",
        "updated_at"
    )
    fields = readonly_fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class AccountAdmin(BaseAccountAdmin):
    form = AccountChangeForm
    add_form = AccountCreationForm

    list_display = (
        "email",
        "username",
        "get_full_name",
        "get_organization",
        "created_at",
        "is_admin",
        "is_subscriber",
        "has_chatbot_access",
    )
    list_filter = (
        SuperUserListFilter,
        "is_admin",
        "profile",
        SubscriptionListFilter,
    )
    readonly_fields = ("uuid", "created_at", "updated_at", "deleted_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "uuid",
                    "username",
                    "email",
                    "password",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                )
            },
        ),
        (
            "Personal",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "full_name",
                    "birth_date",
                    "picture",
                    "twitter",
                    "linkedin",
                    "github",
                    "website",
                    "description",
                    "description_pt",
                    "description_en",
                    "description_es",
                    "profile",
                )
            },
        ),
        (
            "Organizations",
            {
                "fields": (
                    "organizations",
                    "groups",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_admin",
                    "is_superuser",
                    "has_chatbot_access",
                    "staff_groups",
                )
            },
        ),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "email",
                    "profile",
                    "password1",
                    "password2",
                    "is_active",
                ),
            },
        ),
    )
    search_fields = ("email", "full_name")
    ordering = ["-created_at"]
    inlines = (CareerInline, SubscriptionInline, DataAPIKeyInline)
    filter_horizontal = ()

    def is_subscriber(self, instance):
        return bool(instance.is_subscriber)

    is_subscriber.boolean = True
    is_subscriber.short_description = "Subscriber"


class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "description",
    )
    search_fields = (
        "name",
        "slug",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ["name"]


class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "description",
    )
    search_fields = (
        "name",
        "slug",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ["name"]


class CareerAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "team_old",
        "team",
        "role_old",
        "role",
        "level",
        "start_at",
        "end_at",
    )
    search_fields = (
        "account__email",
        "team_old",
        "team__name",
        "role_old",
        "role__name",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ["account", "start_at"]


class SubscriptionAdmin(admin.ModelAdmin):
    actions = [sync_subscription]
    list_display = (
        "admin_email",
        "stripe_subscription",
        "stripe_subscription_status",
        "stripe_subscription_created_at",
    )
    list_filter = (SubscriptionStatusListFilter,)
    search_fields = ("admin__full_name",)
    readonly_fields = (
        "id",
        "admin",
        "subscription",
    )
    ordering = ["-subscription__created"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DataAPIKeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "account",
        "prefix",
        "is_active",
        "expires_at",
        "last_used_at",
        "created_at"
    )
    list_filter = ("is_active",)
    search_fields = ("name", "prefix", "account__email", "account__full_name")
    readonly_fields = (
        "id",
        "prefix",
        "hashed_key",
        "last_used_at",
        "created_at",
        "updated_at"
    )
    fieldsets = (
        (None, {
            "fields": (
                "id",
                "account",
                "name",
                "prefix",
                "hashed_key",
                "is_active",
            )
        }),
        ("Timing", {
            "fields": (
                "expires_at",
                "last_used_at",
                "created_at",
                "updated_at"
            )
        }),
    )
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False  # API keys should be created through the API, not admin


admin.site.register(Account, AccountAdmin)
admin.site.register(Career, CareerAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(DataAPIKey, DataAPIKeyAdmin)
admin.site.register(BDGroup)
admin.site.register(BDRole)