from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status
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


@extend_schema(
    tags=["auth"],
    summary="Register a new donor",
    description=(
        "Create a donor account. The national code is used as the username. "
        "Password must be at least 8 characters and include lowercase, "
        "uppercase, a number, and a special character."
    ),
    request=DonorRegisterSerializer,
    responses={
        201: DonorRegisterSerializer,
        400: OpenApiResponse(
            response=inline_serializer(
                name="DonorRegisterError",
                fields={
                    "detail": serializers.CharField(required=False),
                    "national_code": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                    "password": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                },
            ),
            description="Validation error (duplicate national code, weak password, etc.).",
        ),
    },
    examples=[
        OpenApiExample(
            "Donor registration payload",
            value={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "national_code": "0123456789",
                "mobile_number": "09123456789",
                "blood_group": "A+",
                "province": "Tehran",
                "password": "Strong#Pass1",
            },
            request_only=True,
        )
    ],
)
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


@extend_schema(
    tags=["auth"],
    summary="Register a new medical staff member",
    description=(
        "Create a medical-staff account attached to an existing medical center "
        "(identified by its `center_id`). The national code is used as the username."
    ),
    request=MedicalStaffRegisterSerializer,
    responses={
        201: MedicalStaffRegisterSerializer,
        400: OpenApiResponse(
            response=inline_serializer(
                name="MedicalStaffRegisterError",
                fields={
                    "center_id": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                    "national_code": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                    "password": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                },
            ),
            description="Validation error.",
        ),
    },
    examples=[
        OpenApiExample(
            "Staff registration payload",
            value={
                "first_name": "Sara",
                "last_name": "Karimi",
                "national_code": "1234567890",
                "mobile_number": "09129876543",
                "center_id": "CTR-001",
                "password": "Strong#Pass1",
            },
            request_only=True,
        )
    ],
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


_login_response = inline_serializer(
    name="LoginResponse",
    fields={
        "refresh": serializers.CharField(),
        "access": serializers.CharField(),
        "user": inline_serializer(
            name="LoginUser",
            fields={
                "id": serializers.IntegerField(),
                "username": serializers.CharField(),
                "role": serializers.ChoiceField(choices=UserRole.choices),
            },
        ),
    },
)


@extend_schema(
    tags=["auth"],
    summary="Log in",
    description=(
        "Authenticate with `identifier` (national code) and `password`. "
        "Returns a JWT access + refresh pair."
    ),
    request=LoginSerializer,
    responses={
        200: _login_response,
        400: OpenApiResponse(description="Invalid credentials or inactive account."),
    },
    examples=[
        OpenApiExample(
            "Login payload",
            value={"identifier": "0123456789", "password": "Strong#Pass1"},
            request_only=True,
        ),
        OpenApiExample(
            "Login response",
            value={
                "refresh": "eyJhbGciOi...refresh...",
                "access": "eyJhbGciOi...access...",
                "user": {"id": 1, "username": "0123456789", "role": "donor"},
            },
            response_only=True,
        ),
    ],
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


@extend_schema(
    tags=["auth"],
    summary="Refresh JWT access token",
    description="Exchange a valid refresh token for a new access token.",
    request=inline_serializer(
        name="TokenRefreshRequest",
        fields={"refresh": serializers.CharField()},
    ),
    responses={
        200: inline_serializer(
            name="TokenRefreshResponse",
            fields={"access": serializers.CharField()},
        ),
        401: OpenApiResponse(description="Refresh token is invalid or expired."),
    },
    examples=[
        OpenApiExample(
            "Refresh payload",
            value={"refresh": "eyJhbGciOi...refresh..."},
            request_only=True,
        )
    ],
)
class TokenRefreshSchemaView(APIView):
    """Schema-only view mirroring SimpleJWT's TokenRefreshView."""
    permission_classes = [AllowAny]

    def post(self, request):
        pass


@extend_schema_view(
    get=extend_schema(
        tags=["auth"],
        summary="Get current account",
        description="Return the authenticated user along with the role-specific profile.",
        responses={
            200: AccountMeSerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    patch=extend_schema(
        tags=["auth"],
        summary="Update current profile",
        description=(
            "Partially update the authenticated user's profile. "
            "Donor and medical-staff profiles expose different fields."
        ),
        request=inline_serializer(
            name="ProfileUpdate",
            fields={
                "first_name": serializers.CharField(required=False),
                "last_name": serializers.CharField(required=False),
                "mobile_number": serializers.CharField(required=False),
                "blood_group": serializers.ChoiceField(
                    choices=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                    required=False,
                ),
                "province": serializers.CharField(required=False),
                "center_id": serializers.CharField(required=False),
            },
        ),
        responses={
            200: AccountMeSerializer,
            400: OpenApiResponse(description="Validation error or unsupported role."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
)
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


@extend_schema(
    tags=["auth"],
    summary="List medical centers",
    description="Public list of all medical centers.",
    responses={200: MedicalCenterSerializer(many=True)},
)
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


def _approve_registration_request(registration_request):
    """Create User + MedicalStaffProfile from a pending request and delete it.

    Raises ValueError if the request is not pending.
    """
    if registration_request.status != StaffRegistrationStatus.PENDING:
        raise ValueError("Registration request is not pending.")

    with transaction.atomic():
        registration_request = StaffRegistrationRequest.objects.select_for_update().get(
            pk=registration_request.pk,
            status=StaffRegistrationStatus.PENDING,
        )
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
    return user


class StaffRegistrationRequestAcceptView(APIView):
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

        user = _approve_registration_request(registration_request)
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
