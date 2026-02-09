# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from ._disable_unhealthy_flow_schedules.service import FlowService


class Command(BaseCommand):
    help = "Disable unhealthy flow schedules"

    def handle(self, *args, **options):
        FlowService().disable_unhealthy_flow_schedules()
