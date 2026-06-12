# api/workspaces/schema_manager.py

import os
import re
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

def run_migrations_on_schema(schema_name):
    validate_schema_name(schema_name)
    create_migration_tracker_table()
    
    # 1. Get list of migrations already applied
    applied = get_applied_migrations(schema_name)
    
    # 2. Locate the migrations folder
    sql_dir = os.path.join(os.path.dirname(__file__), 'sql')
    if not os.path.exists(sql_dir):
        return
        
    migration_files = sorted([f for f in os.listdir(sql_dir) if f.endswith('.sql')])
    
    # 3. Apply unapplied migrations
    for filename in migration_files:
        if filename not in applied:
            filepath = os.path.join(sql_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
            # Execute migration atomically on the schema
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # Route search path
                        cursor.execute(f"SET search_path TO {schema_name}, public;")
                        # Execute SQL statements
                        cursor.execute(sql_content)
                        # Record migration
                        cursor.execute(
                            "INSERT INTO public.tenant_migrations (schema_name, migration_name) VALUES (%s, %s);",
                            [schema_name, filename]
                        )
            except Exception as e:
                # Connection might be in failed transaction state, so trigger reset just in case
                reset_search_path()
                raise RuntimeError(f"Error applying SQL migration '{filename}' on schema '{schema_name}': {e}") from e
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
