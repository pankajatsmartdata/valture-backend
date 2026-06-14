# api/workspaces/schema_manager.py

import re
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from valture.db_routers import _local

def validate_schema_name(schema_name):
    # Standard postgres identifier check for security
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema_name):
        raise ValueError(f"Invalid schema name: {schema_name}")

def run_migrations_on_schema(schema_name, target_migration=None):
    validate_schema_name(schema_name)
    
    _local.running_tenant_migration = True
    try:
        # 1. Route to the tenant schema search path
        set_search_path(schema_name)
        
        # 2. Ensure django_migrations table exists in this schema
        recorder = MigrationRecorder(connection)
        recorder.ensure_schema()
        
        # 3. Synchronize public migrations to this tenant schema's tracker
        # so Django knows public-schema dependencies are already satisfied.
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied)
                SELECT pm.app, pm.name, pm.applied 
                FROM public.django_migrations pm
                WHERE pm.app != 'workspace_tenant'
                  AND NOT EXISTS (
                      SELECT 1 FROM django_migrations tm 
                      WHERE tm.app = pm.app AND tm.name = pm.name
                  );
            """)
        
        # 4. Initialize Executor
        executor = MigrationExecutor(connection)
        
        # Resolve targets
        graph = executor.loader.graph
        if target_migration is not None:
            target_migration = str(target_migration).strip()
            if target_migration.lower() == 'zero':
                targets = [('workspace_tenant', None)]
            else:
                matched = [
                    m[1] for m in graph.nodes 
                    if m[0] == 'workspace_tenant' and m[1].startswith(target_migration)
                ]
                if not matched:
                    raise ValueError(f"Target migration '{target_migration}' not found in workspace_tenant migrations.")
                targets = [('workspace_tenant', matched[0])]
        else:
            # Default: run up to latest leaf nodes of workspace_tenant
            targets = [
                (app, name) for app, name in graph.leaf_nodes()
                if app == 'workspace_tenant'
            ]
            
        # 5. Run the migration
        executor.migrate(targets)
        
    except Exception as e:
        reset_search_path()
        raise RuntimeError(f"Error migrating schema '{schema_name}': {e}") from e
    finally:
        reset_search_path()
        _local.running_tenant_migration = False

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

def set_search_path(schema_name):
    validate_schema_name(schema_name)
    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {schema_name}, public;")

def reset_search_path():
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO public;")


