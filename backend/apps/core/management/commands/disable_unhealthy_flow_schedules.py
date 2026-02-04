# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from ._disable_unhealthy_flow_schedules.service import FlowService


class Command(BaseCommand):
    help = "Disable unhealthy flow schedules"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log flows that would be disabled without disabling them",
        )

    def handle(self, *args, **options):
        FlowService().disable_unhealthy_flow_schedules(dry_run=options["dry_run"])
