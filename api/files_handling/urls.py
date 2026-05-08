from django.urls import path
from .views import FilesProcessAPIView

urlpatterns = [
    # path("fetch", name="fetch-files"),
    path("upload", FilesProcessAPIView.as_view(), name="upload-files")
]
