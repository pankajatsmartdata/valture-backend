from django.urls import path, include

urlpatterns = [
    path('files/', include("api.files_handling.urls")),
    path('', include("api.users.urls")),
    path('', include("api.workspaces.urls")),
    path('', include("api.workspace_tenant.urls")),
]