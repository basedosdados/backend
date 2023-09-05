# -*- coding: utf-8 -*-
from django import setup
from django.conf import settings
from django.db import connection

setup()


def run():
    """Clean development database restrictions"""
    with connection.cursor() as cursor:
        print("Cleaning database")
        if "postgres" in settings.DATABASES["default"]["ENGINE"]:
            cursor.execute("TRUNCATE auth_permission")
            cursor.execute("TRUNCATE django_admin_log")
            cursor.execute("TRUNCATE django_content_type")
        if "sqlite" in settings.DATABASES["default"]["ENGINE"]:
            cursor.execute("DELETE FROM auth_permission")
            cursor.execute("DELETE FROM django_admin_log")
            cursor.execute("DELETE FROM django_content_type")
        print("Finished cleaning database")


if __name__ == "__main__":
    run()
