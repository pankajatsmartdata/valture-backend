from rest_framework import generics, permissions
from .models import Workspace
from .serializers import WorkspaceSerializer


class WorkspaceListCreateView(generics.ListCreateAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        # Return only workspaces where user is mapped
        return Workspace.objects.filter(user_mappings__user=self.request.user)


class WorkspaceDetailView(generics.RetrieveAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def get_queryset(self):
        # Queryset limited to user's workspaces
        return Workspace.objects.filter(user_mappings__user=self.request.user)
