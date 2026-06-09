from django.urls import path
from .views import WorkspaceListCreateView, WorkspaceDetailView

urlpatterns = [
    path('workspaces/', WorkspaceListCreateView.as_view(), name='workspaces-list-create'),
    path('workspaces/<uuid:id>/', WorkspaceDetailView.as_view(), name='workspaces-detail'),
]
