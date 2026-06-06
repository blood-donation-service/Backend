from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserRole
from .serializers import (
    AccountMeSerializer,
    DonorProfileSerializer,
    DonorRegisterSerializer,
    LoginSerializer,
    MedicalCenterLookupSerializer,
    MedicalCenterProfileSerializer,
    MedicalCenterRegisterSerializer,
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


class MedicalCenterRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MedicalCenterRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(
            MedicalCenterRegisterSerializer(profile).data,
            status=status.HTTP_201_CREATED,
        )


class MedicalCenterLookupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MedicalCenterLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
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
        elif request.user.role == UserRole.MEDICAL_CENTER:
            serializer = MedicalCenterProfileSerializer(
                request.user.medical_center_profile,
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
