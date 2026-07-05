from rest_framework import serializers
from django.utils import timezone

from accounts.serializers import (
    MedicalCenterSerializer,
    DonorProfileSerializer,
)
from .models import (
    BloodRequest,
    Donation,
    DonationStatus,
)


class BloodRequestSerializer(serializers.ModelSerializer):
    medical_center = MedicalCenterSerializer(read_only=True)

    class Meta:
        model = BloodRequest
        fields = [
            "id",
            "medical_center",
            "title",
            "blood_group",
            "total_capacity",
            "remaining_capacity",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BloodRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodRequest
        fields = [
            "title",
            "blood_group",
            "total_capacity",
        ]


class BloodRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodRequest
        fields = [
            "title",
            "total_capacity",
        ]


class DonationSerializer(serializers.ModelSerializer):
    request = BloodRequestSerializer(read_only=True)

    class Meta:
        model = Donation
        fields = [
            "id",
            "request",
            "status",
            "registered_at",
            "donated_at",
            "cancelled_at",
            "updated_at",
        ]
        read_only_fields = fields


class DonationStaffSerializer(serializers.ModelSerializer):
    donor = DonorProfileSerializer(read_only=True)

    class Meta:
        model = Donation
        fields = [
            "id",
            "donor",
            "status",
            "registered_at",
            "donated_at",
            "cancelled_at",
            "updated_at",
        ]
        read_only_fields = fields


class DonationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = [
            "status",
        ]

    def validate_status(self, value):
        if value != DonationStatus.DONATED:
            raise serializers.ValidationError(
                "Only DONATED is allowed."
            )
        return value

    def update(self, instance, validated_data):
        if instance.status != DonationStatus.PENDING:
            raise serializers.ValidationError(
                "Only pending donations can be marked as donated."
            )

        instance.status = DonationStatus.DONATED
        instance.donated_at = timezone.now()

        instance.save(
            update_fields=[
                "status",
                "donated_at",
            ]
        )

        return instance
