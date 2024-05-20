# -*- coding: utf-8 -*-

from datetime import datetime
from json import dump, load

from django.core.management.base import CommandParser
from django.core.management.commands.dumpdata import Command as DumpDataCommand
from faker import Faker
from loguru import logger

fake = Faker("pt_BR")

logger = logger.bind(module="core")


def empty():
    ts = datetime.now()
    ts = ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return {
        "birth_date": None,
        "created_at": ts,
        "description": None,
        "description_en": None,
        "description_es": None,
        "description_pt": None,
        "email": fake.unique.email(),
        "first_name": fake.first_name(),
        "full_name": None,
        "github": None,
        "is_active": False,
        "is_admin": False,
        "is_superuser": False,
        "last_login": ts,
        "last_name": fake.last_name(),
        "linkedin": None,
        "organizations": [],
        "password": fake.password(),
        "picture": "",
        "twitter": None,
        "updated_at": ts,
        "username": fake.unique.user_name(),
        "uuid": fake.uuid4(),
        "website": None,
    }


class Command(DumpDataCommand):
    """Dump data, avoiding profiles"""

    def add_arguments(self, parser: CommandParser):
        super().add_arguments(parser)
        parser.add_argument(
            "--anonymize",
            dest="anonymize",
            action="store_true",
            help="Anonymize account fixtures with fake data",
        )

    def handle(self, *args, **options) -> str | None:
        logger.info("Dump fixtures")
        response = super().handle(*args, **options)

        if options["anonymize"]:
            logger.info("Filter fixtures")
            output = options["output"]
            with open(output, "r") as file:
                data = load(file)
            for datum in data:
                if datum["model"] == "account.account":
                    if datum["fields"]["profile"] in (2, 3):
                        datum["fields"] = {**datum["fields"], **empty()}
            with open(output, "w") as file:
                dump(data, file)

        return response
