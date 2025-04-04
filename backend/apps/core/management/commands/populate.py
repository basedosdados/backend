# -*- coding: utf-8 -*-
import json
import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, models
from tqdm import tqdm


class BulkUpdate:
    """
    Optimized bulk update functionality with automatic memory management
    """
    def __init__(self):
        self.instances = {}

    def add(self, instance, field_name):
        """Add instance for bulk update"""
        if field_name == 'id' or field_name == instance._meta.pk.name:
            return  # Skip primary key fields
        
        key = f"{instance.__class__.__name__}.{field_name}"
        self.instances.setdefault(key, []).append(instance)

        # Auto-flush when reaching chunk size
        if len(self.instances[key]) >= 1000:
            self._flush_namespace(key)

    def _flush_namespace(self, namespace):
        """Process a batch of updates"""
        if namespace in self.instances and self.instances[namespace]:
            model = self.instances[namespace][0].__class__
            field_name = namespace.split(".")[1]
            model.objects.bulk_update(self.instances[namespace], [field_name])
            self.instances[namespace] = []  # Clear processed instances

    def bulk_update(self):
        """Process all remaining updates"""
        for namespace in list(self.instances.keys()):
            self._flush_namespace(namespace)

class Command(BaseCommand):
    help = "Optimized database population script"

    def _manage_constraints(self, table_name, column_name, enable=True):
        """
        Unified constraint management (enable/disable NOT NULL)
        Returns True if operation succeeded
        """
        if column_name.lower() == "id":
            return False  # Never modify ID column constraints

        mode = 'origin' if enable else 'replica'
        action = 'SET' if enable else 'DROP'
        verb = 'Enabled' if enable else 'Disabled'

        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SET session_replication_role = '{mode}';")
                if enable:
                    cursor.execute(f"""ALTER TABLE "{table_name}" ENABLE TRIGGER ALL;""")
                
                # Check current nullable status
                cursor.execute(f"""
                    SELECT is_nullable FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND column_name = '{column_name}';
                """)
                result = cursor.fetchone()

                if not result:
                    self.stdout.write(self.style.WARNING(
                        f"Column {column_name} not found in {table_name}"
                    ))
                    return False

                current_nullable = result[0] == 'YES'
                target_nullable = not enable

                if current_nullable != target_nullable:
                    cursor.execute(f"""
                        ALTER TABLE "{table_name}" 
                        ALTER COLUMN "{column_name}" {action} NOT NULL;
                    """)
                    self.stdout.write(self.style.SUCCESS(
                        f"{verb} NOT NULL for {column_name} in {table_name}"
                    ))
                    return True
                return False

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Failed to {verb.lower()} constraint on {table_name}.{column_name}: {e}"
            ))
            return False

    def _process_table_data(self, file_path):
        """Load and process table data with memory efficiency"""
        try:
            if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 10MB
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        yield json.loads(line)
            else:
                with open(file_path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading {file_path}: {e}"))
            print('error 1: process table data')
            return []

    def clean_database(self, items):
        """
        Efficient database cleaning with proper cursor handling
        """
        # Disable constraints
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET session_replication_role = 'replica';")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error disabling constraints: {e}"))
            print('error 2: clean database')
            return

        # Process tables
        for item in items:
            table_name = f'"{item}"' if isinstance(item, str) else f'"{item._meta.db_table}"'
            
            try:
                # Try TRUNCATE first (faster)
                with connection.cursor() as cursor:
                    cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
                    self.stdout.write(self.style.SUCCESS(f"Truncated {table_name}"))
            except Exception:
                try:
                    # Fallback to DELETE if TRUNCATE fails
                    with connection.cursor() as cursor:
                        cursor.execute(f"DELETE FROM {table_name};")
                        self.stdout.write(self.style.SUCCESS(f"Cleared {table_name} (using DELETE)"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Failed to clean {table_name}: {e}"
                    ))

        # Re-enable constraints
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET session_replication_role = 'origin';")
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Error re-enabling constraints: {e}"
            ))

    def _create_record(self, model, item, bulk, table_name=None):
        """Create a single database record"""
        if not table_name:
            table_name = f'"{model._meta.db_table}"' if model else None
            if not table_name:
                raise ValueError("Either model or table_name must be provided.")

        fields = []
        values = []
        
        for field_name, field_value in item.items():
            if field_value is None:
                continue

            if model:
                try:
                    field = model._meta.get_field(field_name)
                    if isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                        if not field_name.endswith("_id"):
                            field_name = f"{field_name}_id"
                except Exception:
                    pass  # Field doesn't exist in model

            fields.append(f'"{field_name}"')
            values.append(field_value)

        if not fields:
            self.stdout.write(self.style.WARNING("No valid fields to insert"))
            return

        query = f"""
            INSERT INTO {table_name} ({", ".join(fields)}) 
            VALUES ({", ".join(["%s"]*len(values))}) 
            RETURNING id;
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, values)
                inserted_id = cursor.fetchone()[0]
                
                if model:
                    instance = model.objects.get(pk=inserted_id)
                    for field_name in [f.strip('"') for f in fields]:
                        if item.get(field_name):
                            bulk.add(instance, field_name)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Insert failed for {table_name}: {e}"))
            print('error 3: create record')

    def handle(self, *args, **options):
        app_name = "v1"
        data_dir = os.path.join(os.getcwd(), "metabase_data")
        
        try:
            # Load models and data files
            app = apps.get_app_config(app_name)
            model_classes = app.get_models()
            json_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
            
            # Map tables to models
            tables = [f.replace(".json", "") for f in json_files]
            models_to_populate = [
                m for m in model_classes 
                if m._meta.db_table in tables
            ]
            tables_without_models = [
                t for t in tables 
                if t not in [m._meta.db_table for m in models_to_populate]
            ]

            # Clean database
            self.stdout.write(self.style.WARNING("Cleaning database..."))
            self.clean_database(models_to_populate[::-1] + tables_without_models)

            # Populate models
            if models_to_populate:
                bulk = BulkUpdate()
                self.stdout.write(self.style.SUCCESS("Populating models..."))
                
                for model in models_to_populate:
                    file_path = os.path.join(data_dir, f"{model._meta.db_table}.json")
                    data = self._process_table_data(file_path)
                    
                    if not data:
                        self.stdout.write(self.style.WARNING(
                            f"No data found for {model._meta.db_table}"
                        ))
                        continue

                    for item in tqdm(data, desc=f"Creating {model.__name__}"):
                        self._create_record(model, item, bulk)

                    bulk.bulk_update()

            # Populate tables without models
            if tables_without_models:
                bulk = BulkUpdate()
                self.stdout.write(self.style.SUCCESS("Populating raw tables..."))
                
                for table in tables_without_models:
                    file_path = os.path.join(data_dir, f"{table}.json")
                    data = self._process_table_data(file_path)
                    
                    if not data:
                        self.stdout.write(self.style.WARNING(
                            f"No data found for {table}"
                        ))
                        continue

                    for item in tqdm(data, desc=f"Creating records in {table}"):
                        self._create_record(None, item, bulk, table_name=table)

                    bulk.bulk_update()

            self.stdout.write(self.style.SUCCESS("Database population completed!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Fatal error: {e}"))
            print('error 4: error general')
            raise