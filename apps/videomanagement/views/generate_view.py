from rest_framework.response import Response
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema

from ..models import TemplatePrompts
from ..swagger_serializers import GenerateSerializer
from ..services.VideoGenerationServices import generate_video
from ..serializers import VideoSerializer


class GenerateView(viewsets.ViewSet):
    serializer_class = GenerateSerializer
    queryset = TemplatePrompts.objects.all()

    @swagger_auto_schema(request_body = GenerateSerializer,
                         operation_description = "This API generates the scenes , the prompt and scene images !")
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data = request.data)
        serializer.is_valid(raise_exception = True)

        video = generate_video(**serializer.data)

        return Response({"message": "The video has been generated successfully",
                         "video": VideoSerializer(video).data
                         })
