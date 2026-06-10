from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.mail import send_mail
from rest_framework import generics, permissions, status
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response

from api.workspaces.models import Workspace, UserWorkspaceMapping
from api.workspaces.schema_manager import set_search_path, reset_search_path
from .models import WorkspaceMember, WorkspaceInvitation
from .serializers import WorkspaceMemberSerializer, WorkspaceInvitationSerializer
from .permissions import IsWorkspaceMember, IsWorkspaceAdminOrOwner


class WorkspaceMemberListView(generics.ListAPIView):
    serializer_class = WorkspaceMemberSerializer
    permission_classes = (permissions.IsAuthenticated, IsWorkspaceMember)

    def get_queryset(self):
        workspace_id = self.kwargs.get('workspace_id')
        workspace = get_object_or_404(Workspace, id=workspace_id)
        set_search_path(workspace.schema_name)
        return WorkspaceMember.objects.all()


class WorkspaceInviteView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsWorkspaceAdminOrOwner)

    def post(self, request, workspace_id, *args, **kwargs):
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        try:
            set_search_path(workspace.schema_name)
            serializer = WorkspaceInvitationSerializer(
                data=request.data,
                context={'workspace': workspace}
            )
            if serializer.is_valid():
                invite = serializer.save()
                
                # Generate join URL with workspace_id in the path
                join_url = f"{settings.FRONTEND_URL}/api/workspaces/{workspace.id}/join/?token={invite.token}"
                
                # Send invitation email (logged to console in development)
                send_mail(
                    subject=f"Invitation to join workspace {workspace.name} - Valture",
                    message=f"You have been invited to join the workspace '{workspace.name}' on Valture. "
                            f"Please join using the following link: {join_url}",
                    from_email=settings.GMAIL,
                    recipient_list=[invite.email],
                    fail_silently=False,
                )
                
                return Response(
                    {"message": f"Invitation sent to {invite.email} successfully."},
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        finally:
            reset_search_path()


class WorkspaceJoinView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, workspace_id, *args, **kwargs):
        token = request.data.get("token") or request.query_params.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        try:
            set_search_path(workspace.schema_name)
            try:
                invite = WorkspaceInvitation.objects.get(token=token, is_accepted=False)
            except (WorkspaceInvitation.DoesNotExist, ValueError):
                return Response(
                    {"error": "Invalid or expired invitation token"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify that the current user's email matches the invite's email
            if request.user.email.lower() != invite.email.lower():
                return Response(
                    {"error": f"This invitation was sent to {invite.email}, but you are logged in as {request.user.email}."},
                    status=status.HTTP_403_FORBIDDEN
                )

            with transaction.atomic():
                # 1. Create central mapping
                mapping, created = UserWorkspaceMapping.objects.get_or_create(
                    user=request.user,
                    workspace=workspace,
                    defaults={'role': invite.role}
                )
                
                # 2. Create tenant membership
                member, member_created = WorkspaceMember.objects.get_or_create(
                    user=request.user,
                    defaults={'email': request.user.email, 'role': invite.role}
                )
                
                # 3. Mark invite accepted
                invite.is_accepted = True
                invite.save()

            return Response(
                {"message": f"Successfully joined workspace '{workspace.name}'."},
                status=status.HTTP_200_OK
            )
        finally:
            reset_search_path()
