from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db import transaction

from .models import (
    MedicalCenter,
    MedicalStaffProfile,
    StaffRegistrationRequest,
    StaffRegistrationStatus,
    User,
    UserRole,
)
from .serializers import (
    AccountMeSerializer,
    DonorProfileSerializer,
    DonorRegisterSerializer,
    LoginSerializer,
    MedicalCenterSerializer,
    MedicalStaffProfileSerializer,
    MedicalStaffRegisterSerializer,
    StaffRegistrationRequestSerializer,
)
from .permissions import IsCenterAdmin


class DonorRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DonorRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(
            DonorRegisterSerializer(profile).data,
            status=status.HTTP_201_CREATED,
        )


class MedicalStaffRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MedicalStaffRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration_request = serializer.save()
        return Response(
            MedicalStaffRegisterSerializer(registration_request).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


class AccountMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AccountMeSerializer(request.user).data)

    def patch(self, request):
        if request.user.role == UserRole.DONOR:
            serializer = DonorProfileSerializer(
                request.user.donor_profile,
                data=request.data,
                partial=True,
            )
        elif request.user.role == UserRole.MEDICAL_STAFF:
            serializer = MedicalStaffProfileSerializer(
                request.user.medical_staff_profile,
                data=request.data,
                partial=True,
            )
        else:
            return Response(
                {"detail": "Unsupported user role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AccountMeSerializer(request.user).data)


class MedicalCenterListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        centers = MedicalCenter.objects.all()
        serializer = MedicalCenterSerializer(centers, many=True)
        return Response(serializer.data)


def _get_admin_center(user):
    return getattr(user, "center_admin_profile", None)


class StaffRegistrationRequestListView(APIView):
    permission_classes = [IsAuthenticated, IsCenterAdmin]

    def get(self, request):
        admin_profile = _get_admin_center(request.user)
        if admin_profile is None:
            return Response(
                {"detail": "No medical center is linked to this admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        requests = StaffRegistrationRequest.objects.filter(
            medical_center=admin_profile.medical_center,
            status=StaffRegistrationStatus.PENDING,
        )
        serializer = StaffRegistrationRequestSerializer(requests, many=True)
        return Response(serializer.data)


class StaffRegistrationRequestAcceptView(APIView):
    permission_classes = [IsAuthenticated, IsCenterAdmin]

    @transaction.atomic
    def post(self, request, pk):
        admin_profile = _get_admin_center(request.user)
        if admin_profile is None:
            return Response(
                {"detail": "No medical center is linked to this admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            registration_request = StaffRegistrationRequest.objects.select_for_update().get(
                pk=pk,
                medical_center=admin_profile.medical_center,
                status=StaffRegistrationStatus.PENDING,
            )
        except StaffRegistrationRequest.DoesNotExist:
            raise NotFound("Registration request not found.")

        user = User(
            username=registration_request.national_code,
            role=UserRole.MEDICAL_STAFF,
        )
        user.password = registration_request.password_hash
        user.save()
        MedicalStaffProfile.objects.create(
            user=user,
            medical_center=registration_request.medical_center,
            first_name=registration_request.first_name,
            last_name=registration_request.last_name,
            national_code=registration_request.national_code,
            mobile_number=registration_request.mobile_number,
        )
        registration_request.delete()
        return Response(
            {
                "detail": "Registration request accepted.",
                "username": user.username,
            },
            status=status.HTTP_200_OK,
        )


class StaffRegistrationRequestRejectView(APIView):
    permission_classes = [IsAuthenticated, IsCenterAdmin]

    def post(self, request, pk):
        admin_profile = _get_admin_center(request.user)
        if admin_profile is None:
            return Response(
                {"detail": "No medical center is linked to this admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            registration_request = StaffRegistrationRequest.objects.get(
                pk=pk,
                medical_center=admin_profile.medical_center,
                status=StaffRegistrationStatus.PENDING,
            )
        except StaffRegistrationRequest.DoesNotExist:
            raise NotFound("Registration request not found.")

        registration_request.delete()
        return Response(
            {"detail": "Registration request rejected."},
            status=status.HTTP_200_OK,
        )
