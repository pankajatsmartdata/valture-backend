# api/workspaces/tenant_migrations/0001_initial.py

from api.workspaces.tenant_migrations.operations import CreateTable

class Migration:
    operations = [
        CreateTable(
            table_name='workspace_members',
            columns=[
                ('id', 'UUID PRIMARY KEY DEFAULT gen_random_uuid()'),
                ('user_id', 'UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE'),
                ('email', 'VARCHAR(254) NOT NULL'),
                ('role', "VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'member'))"),
                ('joined_at', 'TIMESTAMPTZ NOT NULL DEFAULT NOW()'),
            ],
            constraints=[
                'UNIQUE(user_id)',
                'UNIQUE(email)'
            ]
        ),
        CreateTable(
            table_name='workspace_invitations',
            columns=[
                ('id', 'UUID PRIMARY KEY DEFAULT gen_random_uuid()'),
                ('email', 'VARCHAR(254) NOT NULL'),
                ('role', "VARCHAR(20) NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member'))"),
                ('token', 'UUID NOT NULL UNIQUE DEFAULT gen_random_uuid()'),
                ('created_at', 'TIMESTAMPTZ NOT NULL DEFAULT NOW()'),
                ('is_accepted', 'BOOLEAN NOT NULL DEFAULT FALSE'),
            ],
            constraints=[
                'UNIQUE(email)'
            ]
        )
    ]
