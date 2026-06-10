from django.core.management.base import BaseCommand
from django.db import connection, transaction
from api.workspaces.models import Workspace
from api.workspaces.schema_manager import create_workspace_schema, set_search_path, reset_search_path

class Command(BaseCommand):
    help = 'Provision schemas for all existing workspaces and migrate their member/invitation data.'

    def handle(self, *args, **options):
        workspaces = Workspace.objects.all()
        self.stdout.write(f"Found {workspaces.count()} workspaces to provision.")
        
        for ws in workspaces:
            self.stdout.write(f"Provisioning schema '{ws.schema_name}' for workspace '{ws.name}'...")
            
            # 1. Create schema and tables
            create_workspace_schema(ws.schema_name)
            
            # 2. Check if there is legacy data in public tables to migrate
            members = []
            invitations = []
            
            # Check public.workspace_member table existence & read data
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        "SELECT id, user_id, email, role, joined_at FROM public.workspace_member WHERE workspace_id = %s",
                        [ws.id]
                    )
                    members = cursor.fetchall()
                except Exception as e:
                    connection.needs_rollback = True
                    # Reset connection state
                    connection.rollback()
                    self.stdout.write(self.style.WARNING(f"Could not read from public.workspace_member: {e}"))

                try:
                    cursor.execute(
                        "SELECT id, email, role, token, created_at, is_accepted FROM public.workspace_invitation WHERE workspace_id = %s",
                        [ws.id]
                    )
                    invitations = cursor.fetchall()
                except Exception as e:
                    connection.needs_rollback = True
                    # Reset connection state
                    connection.rollback()
                    self.stdout.write(self.style.WARNING(f"Could not read from public.workspace_invitation: {e}"))
            
            # 3. Insert into the workspace schema tables
            if members or invitations:
                try:
                    set_search_path(ws.schema_name)
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            for member in members:
                                cursor.execute(
                                    f"INSERT INTO {ws.schema_name}.workspace_members (id, user_id, email, role, joined_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                                    [member[0], member[1], member[2], member[3], member[4]]
                                )
                            for invite in invitations:
                                cursor.execute(
                                    f"INSERT INTO {ws.schema_name}.workspace_invitations (id, email, role, token, created_at, is_accepted) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                                    [invite[0], invite[1], invite[2], invite[3], invite[4], invite[5]]
                                )
                    self.stdout.write(self.style.SUCCESS(f"Migrated {len(members)} members and {len(invitations)} invitations for '{ws.name}'."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to migrate data for '{ws.name}': {e}"))
                finally:
                    reset_search_path()
            else:
                self.stdout.write(f"No legacy data to migrate for '{ws.name}'.")
        
        self.stdout.write(self.style.SUCCESS("All schemas provisioned successfully!"))
