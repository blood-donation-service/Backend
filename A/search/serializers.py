from rest_framework import serializers
from blood.models import BloodRequest


class BloodRequestSearchSerializer(serializers.ModelSerializer):
    medical_center = serializers.CharField(
        source="medical_center.name", read_only=True)
    province = serializers.CharField(
        source="medical_center.province", read_only=True)
    address = serializers.CharField(
        source="medical_center.address", read_only=True)
    phone_number = serializers.CharField(
        source="medical_center.phone_number", read_only=True)

    class Meta:
        model = BloodRequest
        fields = (
            "id",
            "title",
            "blood_group",
            "total_capacity",
            "remaining_capacity",
            "status",
            "medical_center",
            "province",
            "address",
            "phone_number",
            "created_at",
        )
