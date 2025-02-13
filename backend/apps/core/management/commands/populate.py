# -*- coding: utf-8 -*-
import json
import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models, transaction
from haystack import connections
from tqdm import tqdm

from backend.apps.api.v1.models import Dataset

ELASTICSEACH_BATCH_SIZE = 500

class BulkUpdate:
    """
    Bulk update model instances
    """

    instances_by_model = {}

    def add(self, instance, field_name):
        model_name = instance.__class__.__name__
        namespace = f"{model_name}.{field_name}"

        if namespace not in self.instances_by_model:
            self.instances_by_model[namespace] = []

        self.instances_by_model[namespace].append(instance)

    def bulk_update(self):
        for namespace, instances in self.instances_by_model.items():
            model = instances[0].__class__
            field_name = namespace.split(".")[1]

            # Bulk update in chunks of 2000 instances
            for i in range(0, len(instances), 2000):
                chunk = instances[i : i + 2000]
                model.objects.bulk_update(chunk, [field_name])


class References:
    """
    Store references between legacy and new ids
    """

    tables = {}

    def add(self, table, legacy_id, new_id):
        if table not in self.tables:
            self.tables[table] = {}

        self.tables[table][legacy_id] = new_id

    def get(self, table, legacy_id):
        if table not in self.tables:
            return None

        return self.tables[table].get(legacy_id)


class Layer:
    """
    Store models in a layer
    """

    models = []
    depth = 1

    def print(self, context):
        for model in self.models:
            context.stdout.write(context.style.SUCCESS(f"{'-' * self.depth * 2} {model.__name__}"))
            for field in model._meta.get_fields():
                if isinstance(field, models.ForeignKey) or isinstance(
                    field, models.ManyToManyField
                ):
                    name = f"{field.name} -> {field.related_model.__name__}"

                    if field.null:
                        context.stdout.write(f"{' ' * self.depth * 2} {name} (nullable)")
                    else:
                        context.stdout.write(
                            context.style.WARNING(f"{' ' * self.depth * 2} {name}")
                        )

class Logger:
    def __init__(self, stdout, style):
        self.stdout = stdout
        self.style = style

    def success(self, message: str):
        self.stdout.write(self.style.SUCCESS(message))

    def warning(self, message: str):
        self.stdout.write(self.style.WARNING(message))

    def error(self, message: str):
        self.stdout.write(self.style.ERROR(message))


def update_elasticsearch_index(logger):
    datasets = Dataset.objects.all()

    for backend_name in connections.connections_info.keys():
        backend = connections[backend_name]
        unified_index = backend.get_unified_index()

        index = unified_index.get_index(Dataset)

        logger.success(f"Limpando índice em backend: {backend_name}")
        index.clear()
        total = datasets.count()

        for start in range(0, total, ELASTICSEACH_BATCH_SIZE):
            batch = datasets[start : start + ELASTICSEACH_BATCH_SIZE]
            logger.success(f"Atualizando {start + 1} até {start + len(batch)} de {total}")
            index.update(batch)

class Command(BaseCommand):
    help = "Populate database with initial data"

    def get_all_files(self):
        directory = os.path.join(os.getcwd(), "metabase_data")
        files = os.listdir(directory)
        self.files = files

    def load_table_data(self, table_name):
        directory = os.path.join(os.getcwd(), "metabase_data")
        with open(f"{directory}/{table_name}.json") as f:
            data = json.load(f)

        return data

    def get_m2m_data(self, table_name, current_table_name, field_name, id):
        cache_context = f"m2m_cache_{table_name}"

        if not hasattr(self, cache_context):
            data = self.load_table_data(table_name)
            cache = {}

            for item in data:
                related_id = item[current_table_name]
                if related_id not in cache:
                    cache[related_id] = []

                cache[related_id].append(item[field_name])

            setattr(self, cache_context, cache)

        return getattr(self, cache_context).get(id, [])

    def model_has_data(self, model_name):
        if f"{model_name}.json" in self.files:
            return True
        return False

    def get_models_without_foreign_keys(self, models_to_populate):
        models_without_foreign_keys = []

        for model in models_to_populate:
            has_foreign_key = False

            for field in model._meta.get_fields():
                if isinstance(field, models.ForeignKey):
                    has_foreign_key = True
                    break

            if not has_foreign_key:
                models_without_foreign_keys.append(model)

        return models_without_foreign_keys

    def get_models_that_depends_on(self, models_to_populate, layer_models):
        leaf_dependent_models = []

        for model in models_to_populate:
            next_layer = False

            for field in model._meta.get_fields():
                if isinstance(field, models.ForeignKey):
                    if field.related_model not in layer_models:
                        next_layer = True
                        break

            if next_layer is False:
                leaf_dependent_models.append(model)

        return leaf_dependent_models

    def sort_models_by_depedencies(self, models_to_populate, other_models):
        sorted_models = []

        while len(models_to_populate) > 0:
        # for vezes in range(len(models_to_populate)):
            for model in models_to_populate:
                has_all_dependencies = True

            for model in models_to_populate:
                for field in model._meta.get_fields():
                    has_all_dependencies = True

                    print(
                        f"Campo: {field}\nModelos a testar: {len(models_to_populate)}\n{'#' * 30}"
                    )

                    if isinstance(field, models.ForeignKey) or isinstance(
                        field, models.ManyToManyField
                    ):
                        if (
                            field.related_model not in other_models
                            and field.related_model not in sorted_models
                            and field.related_model != model
                            and field.null is False
                        ):
                            has_all_dependencies = False

                if has_all_dependencies:
                    sorted_models.append(model)
                    models_to_populate.remove(model)

        # sorted_models = sorted_models + models_to_populate
        print(f"SORTED MODELS: {sorted_models}\n\n")
        print(f"MODELS TO POPULATE: {models_to_populate}\n\n")

        return sorted_models

    def clean_database(self, _models):
        """
        Clean database
        """
        for model in tqdm(_models, desc="Set foreign keys to null"):
            foreign_keys = [
                field
                for field in model._meta.get_fields()
                if isinstance(field, models.ForeignKey) and field.null is True
            ]
            if foreign_keys:
                field_names = [field.name for field in foreign_keys]
                model.objects.update(**{field_name: None for field_name in field_names})

        for model in tqdm(_models, desc="Cleaning database"):
            with transaction.atomic():
                model.objects.all().delete()

    def create_instance(self, model, item):
        payload = {}
        retry = None
        table_name = model._meta.db_table
        m2m_payload = {}

        for field in model._meta.get_fields():
            if isinstance(field, models.ForeignKey):
                field_name = f"{field.name}_id"
                current_value = item.get(field_name)

                if current_value is None:
                    continue

                reference = self.references.get(field.related_model._meta.db_table, current_value)

                if reference:
                    payload[field_name] = reference
                else:
                    # If the field is required and the reference is missing, we need to skip
                    if field.null is False:
                        return

                    retry = {
                        "item": item,
                        "table_name": field.related_model._meta.db_table,
                        "field_name": field_name,
                    }
            elif isinstance(field, models.ManyToManyField):
                field_name = field.name
                m2m_table_name = field.m2m_db_table()

                current_model_name = f"{model.__name__.lower()}_id"
                field_model_name = field.related_model.__name__.lower() + "_id"

                m2m_related_data = self.get_m2m_data(
                    m2m_table_name, current_model_name, field_model_name, item["id"]
                )

                instances = [
                    self.references.get(field.related_model._meta.db_table, current_value)
                    for current_value in m2m_related_data
                ]

                if instances:
                    m2m_payload[field_name] = instances
            else:
                current_value = item.get(field.name)

                if current_value is None:
                    continue

                payload[field.name] = current_value

        instance = model(**payload)
        instance.save()

        # Set many to many relationships
        if m2m_payload:
            for field_name, related_data in m2m_payload.items():
                field = getattr(instance, field_name)

                try:
                    field.set(related_data)
                except Exception as e:
                    print(e)
                    print(field_name)
                    print(related_data)
                    raise e

        if retry:
            retry["instance"] = instance
            self.retry_instances.append(retry)

        self.references.add(table_name, item["id"], instance.id)

    def handle(self, *args, **kwargs):
        app_name = "v1"
        logger = Logger()

        app = apps.get_app_config(app_name)
        self.get_all_files()
        models_to_populate = []

        for model in app.get_models():
            table_name = model._meta.db_table

            if self.model_has_data(table_name):
                models_to_populate.append(model)
            else:
                logger.warning(f"No data for {table_name}")

        logger.success(f"Will populate {len(models_to_populate)} models")

        leaf_layer = Layer()
        leaf_layer.models = self.get_models_without_foreign_keys(models_to_populate)

        # Remove leaf layer models from models_to_populate
        models_to_populate = list(set(models_to_populate) - set(leaf_layer.models))
        leaf_layer.print(self)

        # Create a layer with models that only depend on the leaf layer
        leaf_dependent_layer = Layer()
        leaf_dependent_layer.depth = 2
        leaf_dependent_layer.models = self.get_models_that_depends_on(
            models_to_populate, leaf_layer.models
        )

        # Remove leaf dependent layer models from models_to_populate
        models_to_populate = list(set(models_to_populate) - set(leaf_dependent_layer.models))
        leaf_dependent_layer.print(self)

        # Sort populated models by dependencies
        sorted_layer = Layer()
        sorted_layer.depth = 3
        sorted_layer.models = self.sort_models_by_depedencies(
            models_to_populate, leaf_layer.models + leaf_dependent_layer.models
        )

        sorted_layer.print(self)
        models_to_populate = list(set(models_to_populate) - set(sorted_layer.models))

        # Populate models
        all_models = leaf_layer.models + leaf_dependent_layer.models + sorted_layer.models

        # Clean database
        # make a copy, dont modify the original array
        reversed_models = all_models.copy()[::-1]
        logger.warning("Cleaning database")
        self.clean_database(reversed_models)
        logger.success("Database cleaned")

        self.references = References()
        # After populating all models, we need to retry the instances that had a missing references
        self.retry_instances = []
        logger.success("Populating models")

        for model in all_models:
            table_name = model._meta.db_table
            data = self.load_table_data(table_name)
            logger.success(f"Populating {table_name}")

            for item in tqdm(data, desc=f"Populating {table_name}"):
                self.create_instance(model, item)

        logger.success("Populating instances with missing references")

        bulk = BulkUpdate()

        for retry in tqdm(self.retry_instances, desc="Retrying instances"):
            item = retry["item"]
            instance = retry["instance"]
            field_name = retry["field_name"]
            related_table_name = retry["table_name"]
            current_value = item.get(field_name)

            reference = self.references.get(related_table_name, current_value)

            if reference:
                setattr(instance, field_name, reference)
                bulk.add(instance, field_name)

        bulk.bulk_update()
        logger.success("Data populated")
        update_elasticsearch_index(logger)
        logger.success("Elasticsearch updated")
