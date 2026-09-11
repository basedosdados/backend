# -*- coding: utf-8 -*-
"""Tests for Account password handling.

Account.save() decides for itself whether self.password holds a plaintext value
to hash or an already-encoded hash to leave alone. Getting that wrong either
stores a password in the clear or double-hashes it and locks the user out, and
neither failure is visible from the outside.
"""

import pytest
from django.contrib.auth.hashers import check_password as django_check_password
from django.contrib.auth.hashers import make_password

from backend.apps.account.models import Account, is_valid_encoded_password, split_password


def make_account(**overrides):
    fields = {
        "username": "john.doe",
        "email": "john.doe@email.com",
        "first_name": "John",
        "last_name": "Doe",
    }
    fields.update(overrides)
    return Account(**fields)


@pytest.mark.django_db
def test_create_user_hashes_the_password():
    account = Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )
    assert account.password != "12345678"
    assert account.check_password("12345678")


@pytest.mark.django_db
def test_plaintext_password_is_hashed_on_save():
    """Assigning a raw password directly must not store it verbatim."""
    account = make_account(password="12345678")
    account.save()
    account.refresh_from_db()
    assert account.password != "12345678"
    assert account.check_password("12345678")


@pytest.mark.django_db
def test_encoded_password_survives_save_unchanged():
    """An already-hashed value must not be hashed a second time."""
    encoded = make_password("12345678")
    account = make_account(password=encoded)
    account.save()
    account.refresh_from_db()
    assert account.password == encoded
    assert account.check_password("12345678")


@pytest.mark.django_db
def test_resaving_does_not_invalidate_the_password():
    account = Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )
    account.first_name = "Johnny"
    account.save()
    account.refresh_from_db()
    assert account.check_password("12345678")


@pytest.mark.django_db
def test_set_password_then_save_is_applied_once():
    account = make_account(password="old-password")
    account.save()
    account.set_password("new-password")
    account.save()
    account.refresh_from_db()
    assert account.check_password("new-password")
    assert not account.check_password("old-password")


@pytest.mark.django_db
def test_new_accounts_are_inactive():
    account = make_account(password="12345678")
    account.save()
    assert account.is_active is False


@pytest.mark.django_db
def test_create_user_rejects_a_missing_email():
    with pytest.raises(ValueError):
        Account.objects.create_user(email="", password="x", username="john.doe")


@pytest.mark.django_db
def test_create_user_rejects_a_missing_username():
    with pytest.raises(ValueError):
        Account.objects.create_user(email="john.doe@email.com", password="x")


@pytest.mark.django_db
def test_deleted_accounts_leave_the_default_queryset():
    account = Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )
    account.delete()
    assert not Account.objects.filter(pk=account.pk).exists()
    assert account.deleted_at is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "first_name,last_name,expected",
    [
        ("John", "Doe", "John Doe"),
        ("John", "", "John"),
        ("", "Doe", "john.doe"),
        ("", "", "john.doe"),
    ],
)
def test_get_full_name(first_name, last_name, expected):
    account = Account(username="john.doe", first_name=first_name, last_name=last_name)
    assert account.get_full_name() == expected


def test_split_password_returns_four_parts():
    algorithm, iterations, salt, hashed = split_password(make_password("12345678"))
    assert algorithm.startswith("pbkdf2")
    assert iterations.isdigit()
    assert salt and hashed


def test_is_valid_encoded_password_accepts_a_django_hash():
    assert is_valid_encoded_password(make_password("12345678")) is True


@pytest.mark.parametrize("value", ["12345678", "", "not$a$hash", "md5$salt$hash"])
def test_is_valid_encoded_password_rejects_non_hashes(value):
    assert is_valid_encoded_password(value) is False


def test_django_and_model_hashers_agree():
    encoded = make_password("12345678")
    assert django_check_password("12345678", encoded)
    assert Account(password=encoded).check_password("12345678")
