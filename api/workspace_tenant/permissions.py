from rest_framework import permissions
from api.workspaces.models import UserWorkspaceMapping


class IsWorkspaceMember(permissions.BasePermission):
    def has_permission(self, request, view):
        workspace_id = view.kwargs.get('workspace_id') or request.data.get('workspace_id')
        if not workspace_id:
            return False
        return UserWorkspaceMapping.objects.filter(
            user=request.user,
            workspace_id=workspace_id
        ).exists()


class IsWorkspaceAdminOrOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        workspace_id = view.kwargs.get('workspace_id') or request.data.get('workspace_id')
        if not workspace_id:
            return False
        return UserWorkspaceMapping.objects.filter(
            user=request.user,
            workspace_id=workspace_id,
            role__in=['owner', 'admin']
        ).exists()
