import re
from django.db import connection

def validate_schema_name(schema_name):
    # Standard postgres identifier check for security
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema_name):
        raise ValueError(f"Invalid schema name: {schema_name}")

def create_workspace_schema(schema_name):
    validate_schema_name(schema_name)
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
        
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.workspace_members (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            email VARCHAR(254) NOT NULL,
            role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
            joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id),
            UNIQUE(email)
        );
        """)
        
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.workspace_invitations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(254) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
            token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_accepted BOOLEAN NOT NULL DEFAULT FALSE,
            UNIQUE(email)
        );
        """)

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
