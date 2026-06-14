# api/workspaces/schema_manager.py

import os
import re
import importlib
from django.db import connection, transaction

def validate_schema_name(schema_name):
    # Standard postgres identifier check for security
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema_name):
        raise ValueError(f"Invalid schema name: {schema_name}")

def create_migration_tracker_table():
    with connection.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public.tenant_migrations (
            id SERIAL PRIMARY KEY,
            schema_name VARCHAR(63) NOT NULL,
            migration_name VARCHAR(100) NOT NULL,
            applied_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (schema_name, migration_name)
        );
        """)

def get_applied_migrations(schema_name):
    create_migration_tracker_table()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT migration_name FROM public.tenant_migrations WHERE schema_name = %s;",
            [schema_name]
        )
        return {row[0] for row in cursor.fetchall()}

def run_migrations_on_schema(schema_name, target_migration=None):
    validate_schema_name(schema_name)
    create_migration_tracker_table()
    
    # 1. Discover all available migrations in tenant_migrations folder
    migrations_dir = os.path.join(os.path.dirname(__file__), 'tenant_migrations')
    if not os.path.exists(migrations_dir):
        return

    # Find files like '0001_initial.py', excluding '__init__.py', 'operations.py', etc.
    migration_files = sorted([
        f for f in os.listdir(migrations_dir)
        if f.endswith('.py') and re.match(r'^\d{4}_', f)
    ])
    
    available_migrations = [f[:-3] for f in migration_files]
    
    # 2. Get currently applied migrations
    applied = get_applied_migrations(schema_name)
    
    # 3. Determine target list of migrations
    if target_migration is not None:
        target_migration = str(target_migration).strip()
        if target_migration.lower() == 'zero':
            target_index = -1
        else:
            target_index = -1
            for idx, name in enumerate(available_migrations):
                if name.startswith(target_migration):
                    target_index = idx
                    break
            if target_index == -1:
                raise ValueError(f"Target migration '{target_migration}' not found in available migrations.")
    else:
        # Default: run up to latest
        target_index = len(available_migrations) - 1

    # 4. Rollback applied migrations that are newer than target
    for idx in range(len(available_migrations) - 1, target_index, -1):
        name = available_migrations[idx]
        if name in applied:
            module = importlib.import_module(f"api.workspaces.tenant_migrations.{name}")
            migration_cls = getattr(module, 'Migration', None)
            if not migration_cls:
                continue
            
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(f"SET search_path TO {schema_name}, public;")
                        # Run operations in reverse order for rollback
                        for operation in reversed(migration_cls.operations):
                            operation.database_backwards(schema_name, cursor)
                        
                        # Remove from tracker
                        cursor.execute(
                            "DELETE FROM public.tenant_migrations WHERE schema_name = %s AND migration_name = %s;",
                            [schema_name, name]
                        )
            except Exception as e:
                reset_search_path()
                raise RuntimeError(f"Error rolling back migration '{name}' on schema '{schema_name}': {e}") from e
            finally:
                reset_search_path()

    # 5. Apply unapplied migrations up to target
    for idx in range(0, target_index + 1):
        name = available_migrations[idx]
        if name not in applied:
            module = importlib.import_module(f"api.workspaces.tenant_migrations.{name}")
            migration_cls = getattr(module, 'Migration', None)
            if not migration_cls:
                continue
            
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(f"SET search_path TO {schema_name}, public;")
                        # Run operations forwards
                        for operation in migration_cls.operations:
                            operation.database_forwards(schema_name, cursor)
                        
                        # Record in tracker
                        cursor.execute(
                            "INSERT INTO public.tenant_migrations (schema_name, migration_name) VALUES (%s, %s);",
                            [schema_name, name]
                        )
            except Exception as e:
                reset_search_path()
                raise RuntimeError(f"Error applying migration '{name}' on schema '{schema_name}': {e}") from e
            finally:
                reset_search_path()

def create_workspace_schema(schema_name):
    validate_schema_name(schema_name)
    
    # 1. Create schema
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
        
    # 2. Apply all migrations
    run_migrations_on_schema(schema_name)

def drop_workspace_schema(schema_name):
    validate_schema_name(schema_name)
    with connection.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")
        cursor.execute("DELETE FROM public.tenant_migrations WHERE schema_name = %s;", [schema_name])

def set_search_path(schema_name):
    validate_schema_name(schema_name)
    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {schema_name}, public;")

def reset_search_path():
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO public;")

