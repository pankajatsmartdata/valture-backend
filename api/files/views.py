from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.request import Request


FILES_STORE = "files_store"

class FilesProcessAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    def post(self, request: Request, *args, **kwargs):
        file_obj = request.FILES.get("file")

        if not file_obj:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with open(f"{FILES_STORE}/{file_obj.name}", "wb+") as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        return Response(
            {"message": "File upload successfully"},
            status=status.HTTP_201_CREATED
        )
