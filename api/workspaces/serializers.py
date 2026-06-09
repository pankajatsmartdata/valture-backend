from django.db import transaction
from rest_framework import serializers
from .models import Workspace, UserWorkspaceMapping
from .utils import generate_unique_slug, generate_unique_schema_name
from api.workspace_tenant.models import WorkspaceMember


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

            # Create tenant membership
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=user,
                email=user.email,
                role='owner'
            )

            return workspace
