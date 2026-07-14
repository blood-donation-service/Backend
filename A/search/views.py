from drf_spectacular.utils import OpenApiParameter, extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from blood.models import BloodRequest, RequestStatus
from .filters import BloodRequestFilter
from .serializers import BloodRequestSearchSerializer


@extend_schema(
    tags=["search"],
    summary="Search blood requests",
    description=(
        "Public search across all blood requests. "
        "Supports the following query parameters:\n\n"
        "- `blood_group` — accepts `A+`, `A-`, ..., `O-` (case insensitive) "
        "or the `a_positive` / `a_negative` / ... form.\n"
        "- `province` — exact (case insensitive) match on the medical center's province."
    ),
    parameters=[
        OpenApiParameter(
            name="blood_group",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter by blood group (e.g. `A+`, `a_positive`).",
            enum=[
                "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-",
                "a+", "a-", "b+", "b-", "ab+", "ab-", "o+", "o-",
                "a_positive", "a_negative", "b_positive", "b_negative",
                "ab_positive", "ab_negative", "o_positive", "o_negative",
            ],
        ),
        OpenApiParameter(
            name="province",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter by medical-center province (case insensitive).",
        ),
    ],
    responses={200: BloodRequestSearchSerializer(many=True)},
)
class BloodRequestSearchView(APIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BloodRequestFilter
    queryset = BloodRequest.objects.none()

    def get(self, request):
        queryset = (
            BloodRequest.objects
            .select_related("medical_center")
            .filter(status=RequestStatus.ACTIVE)
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
