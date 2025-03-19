# -*- coding: utf-8 -*-
import json
import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, models, transaction
from tqdm import tqdm


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

            # Bulk update in chunks of 1000 instances
            for i in range(0, len(instances), 1000):
                chunk = instances[i : i + 1000]
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


class Command(BaseCommand):
    help = "Populate database with initial data"

    def enable_not_null_if_exists(self, table_name, column_name):
        """
        Verifica se a coluna deve ter uma restrição NOT NULL e, se necessário, reabilita-a.
        A restrição NOT NULL só será reativada se não houver valores nulos na coluna.
        """
        with connection.cursor() as cursor:
            cursor.execute("SET session_replication_role = 'origin';")
            cursor.execute(f"""ALTER TABLE "{table_name}" ENABLE TRIGGER ALL;""")

            # Verifica se a coluna deve ter a restrição NOT NULL
            cursor.execute(
                f"""
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                  AND column_name = '{column_name}';
                """
            )
            result = cursor.fetchone()

            if result and result[0] == "YES":  # 'YES' significa que a coluna permite NULL
                # Verifica se há valores nulos na coluna
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM "{table_name}"
                    WHERE "{column_name}" IS NULL;
                    """
                )
                null_count = cursor.fetchone()[0]

                if null_count == 0:
                    # Reabilita a restrição NOT NULL, pois não há valores nulos
                    cursor.execute(
                        f"""ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" SET NOT NULL;"""
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Restrição NOT NULL reabilitada para a coluna {column_name} na tabela {table_name}."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"A coluna {column_name} na tabela {table_name} possui {null_count} valores nulos. "
                            f"A restrição NOT NULL não foi reativada."
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"A coluna {column_name} na tabela {table_name} já possui restrição NOT NULL ou não existe."
                    )
                )

    def disable_not_null_if_exists(self, table_name, column_name):
        """
        Desabilita a restrição NOT NULL para uma coluna, exceto se o nome da coluna for 'ID'.
        """
        # Verifica se o nome da coluna é 'ID' (ignora maiúsculas/minúsculas)
        if column_name.lower() == "id":
            self.stdout.write(
                self.style.WARNING(
                    f"A coluna {column_name} na tabela {table_name} é 'ID'. A restrição NOT NULL será mantida."
                )
            )
            return  # Não faz nada para colunas com o nome 'ID'

        with connection.cursor() as cursor:
            cursor.execute("SET session_replication_role = 'replica';")
            # Verifica se a coluna possui a restrição NOT NULL
            cursor.execute(
                f"""
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                  AND column_name = '{column_name}';
                """
            )
            result = cursor.fetchone()

            if (
                result and result[0] == "NO" and column_name.lower() != "id"
            ):  # 'NO' significa que a coluna é NOT NULL
                # Desabilita a restrição NOT NULL
                cursor.execute(
                    f"""ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" DROP NOT NULL;"""
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Restrição NOT NULL desabilitada para a coluna {column_name} na tabela {table_name}."
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"A coluna {column_name} na tabela {table_name} não possui restrição NOT NULL ou não existe."
                    )
                )

    def disable_constraints(self, all_models):
        for model in all_models:
            table_name = model._meta.db_table
            for field in model._meta.get_fields():
                if isinstance(field, models.Field) and field.null is False:
                    self.disable_not_null_if_exists(table_name, field.column)

    def enable_constraints(self, all_models):
        for model in all_models:
            table_name = model._meta.db_table
            for field in model._meta.get_fields():
                if isinstance(field, models.Field) and field.null is False:
                    self.enable_not_null_if_exists(table_name, field.column)

    def get_all_files(self):
        directory = os.path.join(os.getcwd(), "metabase_data")
        files = [
            f for f in os.listdir(directory) if f.endswith(".json")
        ]  # Filtra apenas arquivos JSON
        self.files = files

    def load_table_data(self, table_name):
        directory = os.path.join(os.getcwd(), "metabase_data")
        for file_name in self.files:
            if file_name.lower() == f"{table_name.lower()}.json":
                with open(f"{directory}/{file_name}", encoding="utf-8") as f:
                    data = json.load(f)
                return data
        return []

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

        # while range(len(models_to_populate)) > 0:
        for _ in range(len(models_to_populate)):
            for model in models_to_populate:
                has_all_dependencies = True

                for field in model._meta.get_fields():
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
                            break

                if has_all_dependencies:
                    sorted_models.append(model)
                    models_to_populate.remove(model)

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

        models_to_delete = [model for model in tqdm(_models, desc="Cleaning database")]

        for model in models_to_delete:
            try:
                with transaction.atomic():
                    model.objects.all().delete()
            except Exception as error:
                self.stdout.write(self.style.ERROR(f"Erro ao excluir {model}: {error}"))
                continue

    def create_instance(self, model, item, bulk, table_name=None):
        """
        Cria uma instância no banco de dados usando cursor.execute e INSERT INTO.

        :param model: O modelo Django que representa a tabela.
        :param item: Um dicionário contendo os dados a serem inseridos.
        :param bulk: Objeto BulkUpdate para coletar instâncias que precisam ser atualizadas.
        :param table_name: Nome da tabela (usado quando não há modelo).
        """
        if model:
            table_name = f'"{model._meta.db_table}"'  # Nome da tabela no banco de dados
        elif table_name:
            table_name = f'"{table_name}"'  # Nome da tabela fornecido diretamente
        else:
            raise ValueError("Either model or table_name must be provided.")

        fields = []  # Lista de colunas
        values = []  # Lista de valores
        placeholders = []  # Placeholders para o INSERT (ex: %s, %s, ...)

        # Itera sobre os campos do modelo
        for field_name, field_value in item.items():
            if field_value is not None:  # Ignora valores nulos
                # Verifica se o campo é uma ForeignKey ou ManyToMany (apenas se houver um modelo)
                if model:
                    try:
                        field = model._meta.get_field(field_name)
                        if isinstance(field, models.ForeignKey) or isinstance(
                            field, models.ManyToManyField
                        ):
                            if not field_name.endswith("_id"):
                                field_name = f"{field_name}_id"  # Adiciona o sufixo '_id' para ForeignKey ou ManyToMany
                    except Exception:
                        pass  # Ignora campos que não existem no modelo

                fields.append(f'"{field_name}"')  # Adiciona o nome do campo
                values.append(field_value)
                placeholders.append("%s")

        # Constrói a query INSERT INTO
        if fields:  # Verifica se há campos para inserir
            fields_str = ", ".join(fields)  # Colunas (ex: "field1, field2, ...")
            placeholders_str = ", ".join(placeholders)  # Placeholders (ex: "%s, %s, ...")
            query = f"""INSERT INTO {table_name} ({fields_str}) VALUES ({placeholders_str}) RETURNING id;"""

            # Executa a query usando cursor.execute
            with connection.cursor() as cursor:
                try:
                    cursor.execute(query, values)
                    inserted_id = cursor.fetchone()[0]  # Obtém o ID da instância inserida
                    self.stdout.write(
                        self.style.SUCCESS(f"Inserted into {table_name} with Values {values}")
                    )
                    if model:
                        instance = model.objects.get(
                            pk=inserted_id
                        )  # Recupera a instância inserida
                        # Adiciona a instância ao BulkUpdate se houver campos para atualizar
                        for field_name in fields:
                            if field_name in item and item[field_name]:
                                bulk.add(instance, field_name)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao inserir em {table_name}: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"No valid fields to insert for {table_name}"))

    def handle(self, *args, **kwargs):
        app_name = "v1"

        app = apps.get_app_config(app_name)
        self.get_all_files()  # Carrega todos os arquivos JSON
        get_models = app.get_models()

        # Lista de tabelas a partir dos nomes dos arquivos JSON
        tables_from_files = [file_name.replace(".json", "") for file_name in self.files]

        # Mapeia os modelos correspondentes às tabelas
        models_to_populate = []
        for model in get_models:
            if model._meta.db_table in tables_from_files:
                models_to_populate.append(model)

        # Remove as tabelas que já têm modelos da lista de tabelas sem modelos
        tables_with_models = [model._meta.db_table for model in models_to_populate]
        tables_without_models = [table for table in tables_from_files if table not in tables_with_models]

        self.stdout.write(self.style.SUCCESS(f"Will populate {len(models_to_populate)} models and {len(tables_without_models)} tables without models."))

        # Popula os modelos correspondentes
        if models_to_populate:
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
            all_models = (
                leaf_layer.models
                + leaf_dependent_layer.models
                + sorted_layer.models
                + models_to_populate
            )

            # make a copy, dont modify the original array and Clean database
            reversed_models = all_models.copy()[::-1]
            self.stdout.write(self.style.WARNING("Cleaning database"))
            self.clean_database(reversed_models)
            self.stdout.write(self.style.SUCCESS("Database cleaned"))

            self.references = References()

            bulk = BulkUpdate()
            self.disable_constraints(all_models)
            for model in all_models:
                table_name = model._meta.db_table
                data = self.load_table_data(table_name)
                if not data:
                    self.stdout.write(self.style.WARNING(f"No data found for {table_name}"))
                    continue

                self.stdout.write(self.style.SUCCESS(f"Populating {table_name}"))

                for item in tqdm(data, desc=f"Creating instance of {table_name}"):
                    try:
                        self.create_instance(model, item, bulk)
                        self.stdout.write(self.style.SUCCESS(f"Populating {table_name}"))
                    except Exception as error:
                        self.stdout.write(
                            self.style.ERROR(f"Erro ao criar instância de {table_name}: {error}")
                        )
                        continue
  
            bulk.bulk_update()

        bulk = BulkUpdate()
        # Popula as tabelas sem modelos correspondentes
        if tables_without_models:
            self.stdout.write(self.style.WARNING("Populating tables without models..."))
            for table_name in tables_without_models:
                data = self.load_table_data(table_name)
                if not data:
                    self.stdout.write(self.style.WARNING(f"No data found for {table_name}"))
                    continue

                self.stdout.write(self.style.SUCCESS(f"Populating {table_name}"))

                for item in tqdm(data, desc=f"Creating instance of {table_name}"):
                    try:
                        self.create_instance(None, item, bulk, table_name=table_name)
                        self.stdout.write(self.style.SUCCESS(f"Populating {table_name}"))
                    except Exception as error:
                        self.stdout.write(
                            self.style.ERROR(f"Erro ao criar instância de {table_name}: {error}")
                        )
                        continue

        bulk.bulk_update()
        self.enable_constraints(all_models)

        self.stdout.write(self.style.SUCCESS("Data populated"))