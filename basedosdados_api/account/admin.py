# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db import models
from martor.widgets import AdminMartorWidget

from basedosdados_api.account.models import Account, BDGroup, BDGroupRole, BDRole, Career


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirme a senha", widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ("email", "username", "first_name", "last_name", "profile")

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
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


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = (
        "email",
        "username",
        "get_full_name",
        "get_organization",
        "is_admin",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")
    list_filter = ("is_admin",)
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
                )
            },
        ),
        (
            "Personal info",
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
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "profile",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)
    filter_horizontal = ()


class BDGroupRoleInline(admin.TabularInline):
    model = BDGroupRole
    extra = 1


class CareerAdmin(admin.ModelAdmin):
    list_display = ("account", "team", "level", "role", "start_at", "end_at")
    search_fields = ("account", "team")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("account", "start_at")


class BDGroupAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {"widget": AdminMartorWidget},
    }
    inlines = (BDGroupRoleInline,)
    list_display = ("name", "description")
    search_fields = ("name", "description")
    ordering = ("name",)


admin.site.register(Account, UserAdmin)
admin.site.register(Career, CareerAdmin)
admin.site.register(BDRole)
admin.site.register(BDGroup, BDGroupAdmin)
