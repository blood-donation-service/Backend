from django.shortcuts import render

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction, IntegrityError
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
    DonationStaffSerializer
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


class BloodRequestDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        blood_request = get_object_or_404(
            BloodRequest.objects.select_related("medical_center"),
            pk=pk,
        )
        serializer = BloodRequestSerializer(blood_request)
        return Response(serializer.data)


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


class RegisterDonationView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        if request.user.role != UserRole.DONOR:
            return Response(
                {"detail": "Only donors can register for donations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        blood_request = get_object_or_404(
            BloodRequest.objects.select_for_update(),
            pk=pk,
            status=RequestStatus.ACTIVE,
        )

        if blood_request.remaining_capacity <= 0:
            return Response(
                {"detail": "This request has no remaining capacity."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Donation.objects.filter(
            donor=request.user.donor_profile,
            request=blood_request,
            status__in=[
                DonationStatus.PENDING,
                DonationStatus.DONATED,
            ],
        ).exists():
            return Response(
                {"detail": "You have already registered for this request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        donation = Donation.objects.create(
            donor=request.user.donor_profile,
            request=blood_request,
        )

        blood_request.remaining_capacity -= 1

        if blood_request.remaining_capacity == 0:
            blood_request.status = RequestStatus.PENDING

        blood_request.save(
            update_fields=[
                "remaining_capacity",
                "status",
            ]
        )

        return Response(
            DonationSerializer(donation).data,
            status=status.HTTP_201_CREATED,
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


class DonationUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        donation = get_object_or_404(
            Donation.objects.select_related("request").select_for_update(),
            pk=pk,
        )

        # Authorization
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

        # Only pending donations can be cancelled
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
