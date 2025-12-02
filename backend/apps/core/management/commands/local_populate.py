# -*- coding: utf-8 -*-
from django.core.management import call_command
from django.core.management.base import BaseCommand
from loguru import logger

from .constants import LocalPolulate
from .utils import download_backup


class Command(BaseCommand):
    help = "Populate local database with initial data from prod"

    def handle(self, *args, **options) -> None:
        download_backup(LocalPolulate.URL_JSON.value, LocalPolulate.PATH_FILE.value)

        logger.info("Purge previous database if exists")
        call_command("flush", interactive=False)

        logger.info("Migrate development database")
        call_command("migrate")

        logger.info("Load data!")
        call_command("loaddata", str(LocalPolulate.PATH_FILE.value))

        logger.info("Atualizar index!")
        call_command("update_index")

        logger.info("Processo concluído com sucesso!")
