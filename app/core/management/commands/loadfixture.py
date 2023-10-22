# -*- coding: utf-8 -*-
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from modeltranslation.management.commands.loaddata import Command as LoadDataCommand

from app.utils import is_prod

IS_SQLITE = "sqlite" in settings.DATABASES.get("default", {}).get("ENGINE")
IS_POSTGRES = "postgres" in settings.DATABASES.get("default", {}).get("ENGINE")

DB_PATH = Path(settings.DATABASES.get("default", {}).get("NAME", "."))
DB_STATEMENT = "TRUNCATE" if IS_POSTGRES and not IS_SQLITE else "DELETE FROM"


class Command(LoadDataCommand):
    """Load data with pre and post processing hooks

    Truncate django content type tables before loading fixtures, and index
    the database after loading fixtures. It's intended to be used only in
    a local development environment. This is necessary because the order
    of migrations execution differ in production and development.

    1. Purge previous database if exists
    2. Migrate development database
    2. Purge database restrictions
    3. Load fixtures
    4. Build index
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--skip-index",
            dest="skip_index",
            action="store_true",
            help="Skip index build after loading fixtures",
        )

    def handle(self, *args, **options) -> str | None:
        if is_prod():
            return None

        print("Purge previous database if exists")
        call_command("flush", interactive=False)

        print("Migrate development database")
        call_command("migrate")

        print("Purge database restrictions")
        with connection.cursor() as cursor:
            cursor.execute(f"{DB_STATEMENT} auth_permission CASCADE")
            cursor.execute(f"{DB_STATEMENT} django_admin_log CASCADE")
            cursor.execute(f"{DB_STATEMENT} django_content_type CASCADE")

        print("Load fixtures")
        response = super().handle(*args, **options)

        if not options["skip_index"]:
            print("Build index")
            try:
                call_command("rebuild_index", interactive=False)
            except Exception:
                pass

        return response
