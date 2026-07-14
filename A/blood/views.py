from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import UserRole
from .models import (
    BloodRequest,
    Donation,
    DonationStatus,
    RequestStatus,
)
from .serializers import (
    BloodRequestSerializer,
    BloodRequestCreateSerializer,
    BloodRequestUpdateSerializer,
    DonationSerializer,
    DonationStatusSerializer,
    DonationStaffSerializer,
)


_FORBIDDEN_DETAIL = inline_serializer(
    name="ForbiddenDetail",
    fields={"detail": serializers.CharField()},
)
_BAD_REQUEST_DETAIL = inline_serializer(
    name="BadRequestDetail",
    fields={"detail": serializers.CharField()},
)
_NOT_FOUND_DETAIL = inline_serializer(
    name="NotFoundDetail",
    fields={"detail": serializers.CharField()},
)


@extend_schema(
    tags=["blood-requests"],
    summary="List active blood requests",
    description=(
        "Public list of blood requests that are still `active` and have "
        "remaining capacity."
    ),
    responses={200: BloodRequestSerializer(many=True)},
)
class BloodRequestListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        requests = (
            BloodRequest.objects.filter(
                status=RequestStatus.ACTIVE,
                remaining_capacity__gt=0,
            )
            .select_related("medical_center")
        )
        serializer = BloodRequestSerializer(requests, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["blood-requests"],
    summary="Retrieve a blood request",
    description="Public detail endpoint for a single blood request.",
    parameters=[
        OpenApiParameter(
            name="pk",
            location=OpenApiParameter.PATH,
            type=int,
            description="Blood request ID.",
        )
    ],
    responses={
        200: BloodRequestSerializer,
        404: OpenApiResponse(
            response=_NOT_FOUND_DETAIL,
            description="Blood request not found.",
        ),
    },
)
class BloodRequestDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        blood_request = get_object_or_404(
            BloodRequest.objects.select_related("medical_center"),
            pk=pk,
        )
        serializer = BloodRequestSerializer(blood_request)
        return Response(serializer.data)


@extend_schema(
    tags=["blood-requests"],
    summary="Create a blood request",
    description=(
        "Medical-staff only. Creates a blood request attached to the caller's "
        "medical center. `remaining_capacity` defaults to `total_capacity`."
    ),
    request=BloodRequestCreateSerializer,
    responses={
        201: BloodRequestSerializer,
        400: OpenApiResponse(description="Validation error."),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(
            response=_FORBIDDEN_DETAIL,
            description="Caller is not medical staff.",
        ),
    },
    examples=[
        OpenApiExample(
            "Create payload",
            value={"title": "Urgent A+ needed",
                   "blood_group": "A+", "total_capacity": 5},
            request_only=True,
        )
    ],
)
class BloodRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != UserRole.MEDICAL_STAFF:
            return Response(
                {"detail": "Only medical staff can create blood requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BloodRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        blood_request = serializer.save(
            medical_center=request.user.medical_staff_profile.medical_center
        )

        return Response(
            BloodRequestSerializer(blood_request).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["blood-requests"],
    summary="Update a blood request",
    description=(
        "Medical-staff only. Partial update of `title` and/or `total_capacity` "
        "(can only be increased). Blood group is immutable."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            location=OpenApiParameter.PATH,
            type=int,
            description="Blood request ID.",
        )
    ],
    request=BloodRequestUpdateSerializer,
    responses={
        200: BloodRequestSerializer,
        400: OpenApiResponse(description="Validation error."),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Caller is not medical staff."),
        404: OpenApiResponse(
            response=_NOT_FOUND_DETAIL,
            description="Blood request not found in caller's medical center.",
        ),
    },
)
class BloodRequestUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != UserRole.MEDICAL_STAFF:
            return Response(
                {"detail": "Only medical staff can update blood requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        blood_request = get_object_or_404(
            BloodRequest,
            pk=pk,
            medical_center=request.user.medical_staff_profile.medical_center,
        )

        serializer = BloodRequestUpdateSerializer(
            blood_request,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(BloodRequestSerializer(blood_request).data)


@extend_schema(
    tags=["blood-requests"],
    summary="Resolve a blood request",
    description=(
        "Medical-staff only. Marks the request as `resolved` once all "
        "donations are complete. The request must belong to the caller's "
        "medical center."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            location=OpenApiParameter.PATH,
            type=int,
            description="Blood request ID.",
        )
    ],
    request=None,
    responses={
        200: BloodRequestSerializer,
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Caller is not medical staff."),
        404: OpenApiResponse(description="Blood request not found."),
    },
)
class ResolveBloodRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != UserRole.MEDICAL_STAFF:
            return Response(
                {"detail": "Only medical staff can resolve blood requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        blood_request = get_object_or_404(
            BloodRequest,
            pk=pk,
            medical_center=request.user.medical_staff_profile.medical_center,
        )

        blood_request.status = RequestStatus.RESOLVED
        blood_request.save()

        return Response(BloodRequestSerializer(blood_request).data)


@extend_schema(
    tags=["donations"],
    summary="Register as a donor for a request",
    description=(
        "Donor only. Registers the caller as a pending donor on the given "
        "active blood request. Decrements `remaining_capacity` by 1. "
        "A donor cannot have more than one active (pending/donated) "
        "donation per request."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            location=OpenApiParameter.PATH,
            type=int,
            description="Blood request ID.",
        )
    ],
    request=None,
    responses={
        201: DonationSerializer,
        400: OpenApiResponse(
            response=_BAD_REQUEST_DETAIL,
            description=(
                "No remaining capacity or duplicate active donation."
            ),
        ),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Caller is not a donor."),
        404: OpenApiResponse(
            response=_NOT_FOUND_DETAIL,
            description="Active blood request not found.",
        ),
    },
)
class RegisterDonationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != UserRole.DONOR:
            return Response(
                {"detail": "Only donors can register for donations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            updated = BloodRequest.objects.filter(
                pk=pk,
                status=RequestStatus.ACTIVE,
                remaining_capacity__gt=0,
            ).update(
                remaining_capacity=F("remaining_capacity") - 1,
            )

            if not updated:
                return Response(
                    {"detail": "This request has no remaining capacity."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            blood_request = BloodRequest.objects.get(pk=pk)

            if Donation.objects.filter(
                donor=request.user.donor_profile,
                request=blood_request,
                status__in=[
                    DonationStatus.PENDING,
                    DonationStatus.DONATED,
                ],
            ).exists():
                transaction.set_rollback(True)
                return Response(
                    {"detail": "You have already registered for this request."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                donation = Donation.objects.create(
                    donor=request.user.donor_profile,
                    request=blood_request,
                )
            except IntegrityError:
                transaction.set_rollback(True)
                return Response(
                    {"detail": "You have already registered for this request."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if blood_request.remaining_capacity == 0:
                BloodRequest.objects.filter(pk=pk).update(
                    status=RequestStatus.PENDING,
                )

        return Response(
            DonationSerializer(donation).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["donations"],
    summary="List my donations",
    description="Donor only. Returns all donations belonging to the caller.",
    responses={
        200: DonationSerializer(many=True),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Caller is not a donor."),
    },
)
class MyDonationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != UserRole.DONOR:
            return Response(
                {"detail": "Only donors can view their donations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        donations = (
            Donation.objects.filter(
                donor=request.user.donor_profile,
            )
            .select_related(
                "request",
                "request__medical_center",
            )
        )

        serializer = DonationSerializer(donations, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["donations"],
    summary="Cancel a donation",
    description=(
        "Cancels a pending donation. Donors may cancel their own donations; "
        "medical staff may cancel donations belonging to their own center. "
        "Only `pending` donations can be cancelled; doing so frees one slot "
        "in the parent blood request."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            location=OpenApiParameter.PATH,
            type=int,
            description="Donation ID.",
        )
    ],
    request=None,
    responses={
        200: DonationSerializer,
        400: OpenApiResponse(
            response=_BAD_REQUEST_DETAIL,
            description="Donation is not in `pending` state.",
        ),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(
            response=_FORBIDDEN_DETAIL,
            description=(
                "Caller may only cancel their own donation (donor) or "
                "donations of their own center (staff)."
            ),
        ),
        404: OpenApiResponse(description="Donation not found."),
    },
)
class DonationUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        donation = get_object_or_404(
            Donation.objects.select_related("request").select_for_update(),
            pk=pk,
        )

        if request.user.role == UserRole.DONOR:
            if donation.donor != request.user.donor_profile:
                return Response(
                    {"detail": "You can only cancel your own donation."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        elif request.user.role == UserRole.MEDICAL_STAFF:
            if (
                donation.request.medical_center
                != request.user.medical_staff_profile.medical_center
            ):
                return Response(
                    {
                        "detail": (
                            "You can only cancel donations for your own medical center."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        else:
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if donation.status != DonationStatus.PENDING:
            return Response(
                {"detail": "Only pending donations can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blood_request = (
            BloodRequest.objects.select_for_update()
            .get(pk=donation.request_id)
        )

        donation.status = DonationStatus.CANCELLED
        donation.cancelled_at = timezone.now()

        donation.save(
            update_fields=[
                "status",
                "cancelled_at",
            ]
        )

        blood_request.remaining_capacity += 1

        if blood_request.status == RequestStatus.PENDING:
            blood_request.status = RequestStatus.ACTIVE

        blood_request.save(
            update_fields=[
                "remaining_capacity",
                "status",
            ]
        )

        return Response(
            DonationSerializer(donation).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["blood-requests"],
    summary="List my medical center's blood requests",
    description=(
        "Medical-staff only. Returns every blood request belonging to the "
        "caller's medical center, regardless of status."
    ),
    responses={
        200: BloodRequestSerializer(many=True),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Caller is not medical staff."),
    },
)
class MedicalCenterRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != UserRole.MEDICAL_STAFF:
            return Response(
                {"detail": "Only medical staff can view their requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        requests = (
            BloodRequest.objects.filter(
                medical_center=request.user.medical_staff_profile.medical_center
            )
            .select_related("medical_center")
            .prefetch_related("donations")
        )

        serializer = BloodRequestSerializer(requests, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["donations"],
    summary="List donors for a blood request",
    description=(
        "Medical-staff only. Returns all donations (with donor profile) "
        "registered for the given request, ordered by most recent."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            location=OpenApiParameter.PATH,
            type=int,
            description="Blood request ID.",
        )
    ],
    responses={
        200: DonationStaffSerializer(many=True),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Caller is not medical staff."),
        404: OpenApiResponse(description="Blood request not found."),
    },
)
class RequestDonorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role != UserRole.MEDICAL_STAFF:
            return Response(
                {"detail": "Only medical staff can view request donors."},
                status=status.HTTP_403_FORBIDDEN,
            )

        blood_request = get_object_or_404(
            BloodRequest,
            pk=pk,
            medical_center=request.user.medical_staff_profile.medical_center,
        )

        donations = (
            Donation.objects.filter(request=blood_request)
            .select_related(
                "donor",
                "donor__user",
            )
            .order_by("-registered_at")
        )

        serializer = DonationStaffSerializer(
            donations,
            many=True,
        )

        return Response(serializer.data)


@extend_schema(
    tags=["donations"],
    summary="Mark a donation as donated",
    description=(
        "Medical-staff only. Transitions a `pending` donation to `donated`. "
        "Only donations belonging to the caller's medical center can be updated."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            location=OpenApiParameter.PATH,
            type=int,
            description="Donation ID.",
        )
    ],
    request=DonationStatusSerializer,
    responses={
        200: DonationSerializer,
        400: OpenApiResponse(
            response=_BAD_REQUEST_DETAIL,
            description="Donation is not in `pending` state.",
        ),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(
            response=_FORBIDDEN_DETAIL,
            description=(
                "Caller is not medical staff, or donation belongs to a "
                "different medical center."
            ),
        ),
        404: OpenApiResponse(description="Donation not found."),
    },
    examples=[
        OpenApiExample(
            "Mark as donated payload",
            value={"status": "donated"},
            request_only=True,
        )
    ],
)
class MarkDonationAsDonatedView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != UserRole.MEDICAL_STAFF:
            return Response(
                {"detail": "Only medical staff can mark donations as donated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        donation = get_object_or_404(
            Donation.objects.select_related("request"),
            pk=pk,
        )

        if (
            donation.request.medical_center
            != request.user.medical_staff_profile.medical_center
        ):
            return Response(
                {
                    "detail": (
                        "You can only update donations for your own medical center."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DonationStatusSerializer(
            donation,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            DonationSerializer(donation).data,
            status=status.HTTP_200_OK,
        )
