from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth import get_user_model
from api.workspaces.models import Workspace, UserWorkspaceMapping
from api.workspace_tenant.models import WorkspaceMember
from api.workspaces.utils import generate_unique_slug, generate_unique_schema_name
from api.workspaces.schema_manager import create_workspace_schema, set_search_path, reset_search_path

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_verified')
        read_only_fields = ('id', 'email', 'is_verified')


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    workspace_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name', 'workspace_name')

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')
        workspace_name = validated_data.get('workspace_name', '')

        with transaction.atomic():
            # 1. Create User
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # 2. Create a workspace (either requested or default)
            if not workspace_name:
                name_part = first_name if first_name else email.split('@')[0]
                workspace_name = f"{name_part.capitalize()}'s Workspace"
            
            slug = generate_unique_slug(workspace_name)
            schema_name = generate_unique_schema_name(slug)

            workspace = Workspace.objects.create(
                name=workspace_name,
                slug=slug,
                schema_name=schema_name
            )

            # Map user to workspace as owner globally
            UserWorkspaceMapping.objects.create(
                user=user,
                workspace=workspace,
                role='owner'
            )

            # 3. Create the database schema and tables
            create_workspace_schema(schema_name)

            # 4. Map user as owner in workspace member table (inside the schema)
            try:
                set_search_path(schema_name)
                WorkspaceMember.objects.create(
                    user=user,
                    email=email,
                    role='owner'
                )
            finally:
                reset_search_path()

            return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Embed default/active workspace ID
        mapping = user.workspace_mappings.order_by('joined_at').first()
        if mapping:
            token['workspace_id'] = str(mapping.workspace.id)
            token['role'] = mapping.role
        else:
            token['workspace_id'] = None
            token['role'] = None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        # Get list of workspaces user belongs to
        mappings = user.workspace_mappings.select_related('workspace').all()
        workspaces_list = []
        for m in mappings:
            workspaces_list.append({
                'id': str(m.workspace.id),
                'name': m.workspace.name,
                'slug': m.workspace.slug,
                'role': m.role
            })

        active_workspace = None
        if mappings.exists():
            first_mapping = mappings.first()
            active_workspace = {
                'id': str(first_mapping.workspace.id),
                'name': first_mapping.workspace.name,
                'slug': first_mapping.workspace.slug,
                'role': first_mapping.role
            }

        data['user'] = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_verified': user.is_verified
        }
        data['active_workspace'] = active_workspace
        data['workspaces'] = workspaces_list
        return data
