from django.urls import path, include

urlpatterns = [
    path('files/', include("api.files.urls"))
]