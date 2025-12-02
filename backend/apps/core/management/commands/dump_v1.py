# -*- coding: utf-8 -*-

from django.core.management import call_command
from django.core.management.base import BaseCommand
from loguru import logger

from .constants import LocalPolulate
from .utils import remove_connection_accounts


class Command(BaseCommand):
    help = "Dump APP v1, avoiding APP accout"

    def handle(self, *args, **options) -> None:
        LocalPolulate.PATH_FILE.value.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Fazendo Dump")
        call_command("dumpdata", "v1", indent=2, output=str(LocalPolulate.PATH_FILE.value))

        logger.info("Removendo conexão com dos dados de V1 com Account")
        remove_connection_accounts(LocalPolulate.PATH_FILE.value)

        logger.info("Processo concluído com sucesso!")
