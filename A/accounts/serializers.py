import re

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    BloodGroup,
    DonorProfile,
    MedicalCenter,
    MedicalStaffProfile,
    User,
    UserRole,
)


PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$")


def validate_strong_password(password):
    if len(password) < 8 or not PASSWORD_PATTERN.match(password):
        raise serializers.ValidationError(
            "Password must be at least 8 characters and include lowercase, "
            "uppercase, number, and special character."
        )
    validate_password(password)
    return password


def build_token_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": UserSerializer(user).data,
    }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "role")
        read_only_fields = fields


class DonorProfileSerializer(serializers.ModelSerializer):
    blood_group = serializers.ChoiceField(choices=BloodGroup.choices)

    class Meta:
        model = DonorProfile
        fields = (
            "first_name",
            "last_name",
            "mobile_number",
            "blood_group",
            "province",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("national_code", "created_at", "updated_at")


class MedicalCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalCenter
        fields = (
            "id",
            "center_id",
            "name",
            "postal_code",
            "address",
            "phone_number",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "center_id", "created_at", "updated_at")


class MedicalStaffProfileSerializer(serializers.ModelSerializer):
    medical_center = MedicalCenterSerializer(read_only=True)
    center_id = serializers.SlugRelatedField(
        slug_field="center_id",
        queryset=MedicalCenter.objects.all(),
        source="medical_center",
        write_only=True,
        required=False,
    )

    class Meta:
        model = MedicalStaffProfile
        fields = (
            "first_name",
            "last_name",
            "national_code",
            "mobile_number",
            "center_id",
            "medical_center",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("national_code", "medical_center",
                            "created_at", "updated_at")


class DonorRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    national_code = serializers.CharField(max_length=10)
    mobile_number = serializers.CharField(max_length=11)
    blood_group = serializers.ChoiceField(choices=BloodGroup.choices)
    province = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value):
        return validate_strong_password(value)

    def validate_national_code(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this national code exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            username=validated_data["national_code"],
            password=password,
            role=UserRole.DONOR,
        )
        profile = DonorProfile.objects.create(user=user, **validated_data)
        return profile

    def to_representation(self, instance):
        return {
            "user": UserSerializer(instance.user).data,
            "profile": DonorProfileSerializer(instance).data,
        }


class MedicalStaffRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    national_code = serializers.CharField(max_length=10)
    mobile_number = serializers.CharField(max_length=11)
    center_id = serializers.CharField(max_length=64)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value):
        return validate_strong_password(value)

    def validate_national_code(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this national code exists.")
        return value

    def validate_center_id(self, value):
        if not MedicalCenter.objects.filter(center_id=value).exists():
            raise serializers.ValidationError(
                "No medical center exists with this center id."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        medical_center = MedicalCenter.objects.get(
            center_id=validated_data.pop("center_id"))
        user = User.objects.create_user(
            username=validated_data["national_code"],
            password=password,
            role=UserRole.MEDICAL_STAFF,
        )
        profile = MedicalStaffProfile.objects.create(
            user=user,
            medical_center=medical_center,
            **validated_data,
        )
        return profile

    def to_representation(self, instance):
        return {
            "user": UserSerializer(instance.user).data,
            "profile": MedicalStaffProfileSerializer(instance).data,
        }


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["identifier"],
            password=attrs["password"],
            request=self.context.get("request"),
        )
        if user is None:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        return build_token_response(validated_data["user"])


class AccountMeSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    profile = serializers.DictField(read_only=True)

    def to_representation(self, instance):
        user = instance
        profile = None
        if user.role == UserRole.DONOR:
            profile = DonorProfileSerializer(user.donor_profile).data
        elif user.role == UserRole.MEDICAL_STAFF:
            profile = MedicalStaffProfileSerializer(
                user.medical_staff_profile).data

        return {
            "user": UserSerializer(user).data,
            "profile": profile,
        }


class MedicalCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalCenter
        fields = [
            "id",
            "center_id",
            "name",
            "address",
            "phone_number",
            "latitude",
            "longitude",
        ]
