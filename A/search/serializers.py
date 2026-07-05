from rest_framework import serializers
from blood.models import BloodRequest


class BloodRequestSearchSerializer(serializers.ModelSerializer):
    medical_center = serializers.CharField(source="medical_center.name")

    class Meta:
        model = BloodRequest
        fields = (
            "id",
            "title",
            "blood_group",
            "remaining_capacity",
            "status",
            "medical_center",
            "created_at",
        )
