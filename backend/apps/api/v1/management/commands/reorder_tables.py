# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from backend.apps.api.v1.models import Dataset, Table


class Command(BaseCommand):
    help = "Reorders tables related to Dataset."

    def add_arguments(self, parser):
        parser.add_argument("dataset_id", type=str, help="ID of the dataset")
        parser.add_argument(
            "ordered_slugs", type=str, nargs="+", help="Ordered tables JSON string"
        )

    def handle(self, dataset_id, *args, **options):
        ordered_slugs = options["ordered_slugs"]

        try:
            dataset = Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Dataset with ID {dataset_id} does not exist"))
            return

        for i, slug in enumerate(ordered_slugs):
            try:
                table = dataset.tables.get(slug=slug)
                table.to(i)
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully moved Table {slug} to position {i}")
                )
            except Table.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Table with slug {slug} does not exist"))
