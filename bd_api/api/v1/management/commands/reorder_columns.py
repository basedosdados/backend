# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from bd_api.api.v1.models import Column, Table


class Command(BaseCommand):
    help = "Reorder columns related to tables."

    def add_arguments(self, parser):
        parser.add_argument("table_id", type=str, help="ID of the table")
        parser.add_argument("ordered_slugs", type=str, nargs="+", help="Ordered list of tables")

    def handle(self, table_id, *args, **options):
        ordered_slugs = options["ordered_slugs"]

        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Table with ID {table_id} does not exist"))
            return

        # TODO improve validation
        for i, column_name in enumerate(ordered_slugs):
            column = Column.objects.get(table=table, name=column_name)
            column.order = i
            column.save()
