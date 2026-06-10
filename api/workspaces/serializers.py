from django.db import transaction
from rest_framework import serializers
from .models import Workspace, UserWorkspaceMapping
from .utils import generate_unique_slug, generate_unique_schema_name
from api.workspace_tenant.models import WorkspaceMember
from api.workspaces.schema_manager import create_workspace_schema, set_search_path, reset_search_path


class WorkspaceSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Workspace
        fields = ('id', 'name', 'slug', 'schema_name', 'created_at', 'updated_at', 'role')
        read_only_fields = ('id', 'slug', 'schema_name', 'created_at', 'updated_at', 'role')

    def get_role(self, obj):
        user = self.context.get('request').user
        if user and not user.is_anonymous:
            try:
                mapping = UserWorkspaceMapping.objects.get(user=user, workspace=obj)
                return mapping.role
            except UserWorkspaceMapping.DoesNotExist:
                return None
        return None

    def create(self, validated_data):
        name = validated_data['name']
        slug = generate_unique_slug(name)
        schema_name = generate_unique_schema_name(slug)
        user = self.context['request'].user

        with transaction.atomic():
            workspace = Workspace.objects.create(
                name=name,
                slug=slug,
                schema_name=schema_name
            )

            # Create public mapping
            UserWorkspaceMapping.objects.create(
                user=user,
                workspace=workspace,
                role='owner'
            )

            # Create the database schema and tables
            create_workspace_schema(schema_name)

            # Create tenant membership inside the new schema
            try:
                set_search_path(schema_name)
                WorkspaceMember.objects.create(
                    user=user,
                    email=user.email,
                    role='owner'
                )
            finally:
                reset_search_path()

            return workspace
