from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import MedicalCenter
from blood.models import BloodRequest
from .serializers import BloodRequestSearchSerializer


def create_medical_center(center_id="CENTER-1", **overrides):
    defaults = {
        "name": "Sina Hospital",
        "postal_code": "1234567890",
        "address": "Tehran, Valiasr",
        "phone_number": "02112345678",
        "province": "Tehran",
    }
    defaults.update(overrides)
    return MedicalCenter.objects.create(center_id=center_id, **defaults)


class SearchSerializerTests(TestCase):
    def test_search_serializer_contains_medical_center_name(self):
        center = create_medical_center(center_id="SEARCH-1")
        request = BloodRequest.objects.create(
            medical_center=center,
            title="Urgent A+ needed",
            blood_group="A+",
            total_capacity=3,
        )
        serializer = BloodRequestSearchSerializer(request)
        self.assertEqual(serializer.data["medical_center"], center.name)


class SearchViewTests(APITestCase):
    def test_search_endpoint_filters_by_blood_group_and_province(self):
        center = create_medical_center(center_id="SEARCH-2")
        BloodRequest.objects.create(
            medical_center=center,
            title="Urgent A+ needed",
            blood_group="A+",
            total_capacity=3,
        )
        BloodRequest.objects.create(
            medical_center=create_medical_center(center_id="SEARCH-3", province="Mashhad"),
            title="Urgent O- needed",
            blood_group="O-",
            total_capacity=2,
        )

        response = self.client.get("/search/blood-requests/?blood_group=A%2B&province=Tehran")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["blood_group"], "A+")
