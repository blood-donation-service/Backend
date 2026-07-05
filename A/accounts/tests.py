from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    DonorProfile,
    MedicalCenter,
    MedicalStaffProfile,
    User,
    UserRole,
)


def create_medical_center(center_id="CENTER-1", **overrides):
    defaults = {
        "name": "Sina Hospital",
        "postal_code": "1234567890",
        "address": "Tehran, Valiasr",
        "phone_number": "02112345678",
    }
    defaults.update(overrides)
    return MedicalCenter.objects.create(center_id=center_id, **defaults)


class AccountAuthAPITests(APITestCase):
    def test_donor_can_register_login_and_get_profile(self):
        register_response = self.client.post(
            "/api/auth/register/donor/",
            {
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "national_code": "1234567890",
                "mobile_number": "09123456789",
                "blood_group": "O+",
                "province": "Tehran",
                "password": "Strong!Pass123",
            },
            format="json",
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(register_response.data["user"]["role"], UserRole.DONOR)
        self.assertTrue(DonorProfile.objects.filter(national_code="1234567890").exists())

        login_response = self.client.post(
            "/api/auth/login/",
            {
                "identifier": "1234567890",
                "password": "Strong!Pass123",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        me_response = self.client.get("/api/accounts/me/")

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["profile"]["blood_group"], "O+")

    def test_medical_staff_can_register_against_existing_medical_center(self):
        create_medical_center(center_id="CENTER-1")
        response = self.client.post(
            "/api/auth/register/staff/",
            {
                "first_name": "Reza",
                "last_name": "Sadeghi",
                "national_code": "9876543210",
                "mobile_number": "09121112233",
                "center_id": "CENTER-1",
                "password": "Strong!Pass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], UserRole.MEDICAL_STAFF)
        self.assertEqual(
            response.data["profile"]["medical_center"]["center_id"], "CENTER-1"
        )
        self.assertTrue(
            MedicalStaffProfile.objects.filter(national_code="9876543210").exists()
        )

    def test_staff_registration_rejects_unknown_center(self):
        response = self.client.post(
            "/api/auth/register/staff/",
            {
                "first_name": "Reza",
                "last_name": "Sadeghi",
                "national_code": "9876543210",
                "mobile_number": "09121112233",
                "center_id": "NOPE-999",
                "password": "Strong!Pass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            "/api/auth/register/donor/",
            {
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "national_code": "1234567890",
                "mobile_number": "09123456789",
                "blood_group": "O+",
                "province": "Tehran",
                "password": "password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.exists())

    def test_authenticated_user_can_patch_own_profile(self):
        user = User.objects.create_user(
            username="1234567890",
            password="Strong!Pass123",
            role=UserRole.DONOR,
        )
        DonorProfile.objects.create(
            user=user,
            first_name="Ali",
            last_name="Ahmadi",
            national_code="1234567890",
            mobile_number="09123456789",
            blood_group="O+",
            province="Tehran",
        )

        self.client.force_authenticate(user=user)
        response = self.client.patch(
            "/api/accounts/me/",
            {"province": "Alborz"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["province"], "Alborz")
