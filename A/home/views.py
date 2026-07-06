from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


@extend_schema(
    tags=["home"],
    summary="Service health check",
    description="Lightweight endpoint that confirms the API is reachable.",
    auth=[],
    responses={
        200: inline_serializer(
            name="HomeResponse",
            fields={"name": serializers.CharField()},
        )
    },
)
class HomePage(APIView):
    permission_classes = []

    def get(self, request):
        return Response({"name": "blood-donation-api"})
