from django.urls import path
from .views import WorkspaceMemberListView, WorkspaceInviteView, WorkspaceJoinView

urlpatterns = [
    path('workspaces/<uuid:workspace_id>/members/', WorkspaceMemberListView.as_view(), name='workspace-members-list'),
    path('workspaces/<uuid:workspace_id>/invite/', WorkspaceInviteView.as_view(), name='workspace-invite'),
    path('workspaces/<uuid:workspace_id>/join/', WorkspaceJoinView.as_view(), name='workspace-join'),
]
