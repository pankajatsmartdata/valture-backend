from rest_framework import serializers
from .models import WorkspaceMember, WorkspaceInvitation
from api.users.serializers import UserSerializer


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ('id', 'workspace', 'user', 'email', 'role', 'joined_at')
        read_only_fields = ('id', 'workspace', 'user', 'joined_at')


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceInvitation
        fields = ('id', 'email', 'role', 'token', 'created_at', 'is_accepted')
        read_only_fields = ('id', 'token', 'created_at', 'is_accepted')

    def validate(self, attrs):
        workspace = self.context.get('workspace')
        email = attrs.get('email')

        # Check if email is already a member
        if WorkspaceMember.objects.filter(workspace=workspace, email=email).exists():
            raise serializers.ValidationError("This email is already a member of the workspace.")

        # Check if email already has a pending invitation
        if WorkspaceInvitation.objects.filter(workspace=workspace, email=email, is_accepted=False).exists():
            raise serializers.ValidationError("This email has already been invited to the workspace.")

        return attrs

    def create(self, validated_data):
        workspace = self.context.get('workspace')
        return WorkspaceInvitation.objects.create(
            workspace=workspace,
            email=validated_data['email'],
            role=validated_data.get('role', 'member')
        )
