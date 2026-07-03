from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from blood.models import BloodRequest
from .filters import BloodRequestFilter
from .serializers import BloodRequestSearchSerializer


class BloodRequestSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = (
            BloodRequest.objects
            .select_related("medical_center")
            .all()
        )

        filtered_queryset = BloodRequestFilter(
            request.GET,
            queryset=queryset,
        ).qs

        serializer = BloodRequestSearchSerializer(
            filtered_queryset,
            many=True,
        )

        return Response(serializer.data)
