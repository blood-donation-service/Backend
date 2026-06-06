from rest_framework import status
from rest_framework.test import APITestCase

from .models import DonorProfile, MedicalCenterProfile, User, UserRole


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

    def test_medical_center_can_register_with_mocked_name_and_address(self):
        response = self.client.post(
            "/api/auth/register/center/",
            {
                "center_id": "CENTER-1",
                "postal_code": "1234567890",
                "phone_number": "02112345678",
                "password": "Strong!Pass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], UserRole.MEDICAL_CENTER)
        self.assertEqual(response.data["profile"]["name"], "Medical Center CENTER-1")
        self.assertTrue(
            MedicalCenterProfile.objects.filter(center_id="CENTER-1").exists()
        )

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
