# /api/workspaces/management/commands/migrate_tenants.py

from django.core.management.base import BaseCommand
from api.workspaces.models import Workspace
from api.workspaces.schema_manager import run_migrations_on_schema

class Command(BaseCommand):
    help = 'Run SQL migrations across all workspace schemas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--target',
            type=str,
            default=None,
            help='Target migration to migrate/rollback to (e.g. 0001 or "zero" to rollback all).'
        )

    def handle(self, *args, **options):
        target = options.get('target')
        workspaces = Workspace.objects.all()
        self.stdout.write(f"Found {workspaces.count()} workspaces to migrate.")
        
        for ws in workspaces:
            target_str = f" to target '{target}'" if target else " to latest"
            self.stdout.write(f"Migrating schema '{ws.schema_name}' for workspace '{ws.name}'{target_str}...")
            try:
                run_migrations_on_schema(ws.schema_name, target_migration=target)
                self.stdout.write(self.style.SUCCESS(f"Successfully migrated schema '{ws.schema_name}'."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating schema '{ws.schema_name}': {e}"))
                
        self.stdout.write(self.style.SUCCESS("All migrations completed successfully!"))

