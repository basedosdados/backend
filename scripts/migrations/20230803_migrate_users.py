from os import getenv
from random import choice
from string import ascii_letters, digits, punctuation

import django
import pandas as pd

django.setup()

from basedosdados_api.account.models import Account


def split(s):
    parts = s.split(" ", 1)
    if len(parts) == 1:
        parts.append("")
    return parts


def make_password():
    characters = ascii_letters + digits + punctuation
    password = ''.join(choice(characters) for _ in range(16))
    return password


def create_users_from_csv(csv_file):
    df = pd.read_csv(csv_file)
    df["name"] = df["name"].astype(str)
    df["fullname"] = df["fullname"].astype(str)
    df["is_active"] = df["state"] == "active"
    df["created_at"] = df["created"]

    for _, row in df.iterrows():
        uuid = row["id"]
        email = row["email"]
        username = row["name"]
        password = make_password()
        full_name = row["fullname"]
        first_name, last_name = split(full_name)
        is_active = row["is_active"]
        created_at = row["created_at"]
        try:
            user = Account.objects.create(
                uuid=uuid,
                email=email,
                password=password,
                username=username,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                is_active=is_active,
                created_at=created_at,
            )

            user.set_password(password)
            user.save()
        except Exception as e:
            print(f"[{email}] {e}")

def run():
    """
    Steps to execute:
    - Set the USERS_FILEPATH environment variable
    - Run with `python manage.py runscript -v3 scripts.migrations.20230803_migrate_users`
    """
    USERS_FILEPATH = getenv("USERS_FILEPATH")
    create_users_from_csv(USERS_FILEPATH)
