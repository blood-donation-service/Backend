from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    DonorProfile,
    MedicalCenter,
    MedicalCenterAdminProfile,
    MedicalStaffProfile,
    StaffRegistrationRequest,
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


def create_center_admin(center, username="admin-1", **overrides):
    user = User.objects.create_user(
        username=username,
        password="Strong!Pass123",
        role=UserRole.CENTER_ADMIN,
        is_staff=True,
    )
    return MedicalCenterAdminProfile.objects.create(
        user=user, medical_center=center, **overrides
    )


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

    def test_staff_registration_creates_pending_request(self):
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
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(
            response.data["medical_center"]["center_id"], "CENTER-1"
        )
        self.assertTrue(
            StaffRegistrationRequest.objects.filter(
                national_code="9876543210"
            ).exists()
        )
        self.assertFalse(User.objects.filter(username="9876543210").exists())
        self.assertFalse(
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
        self.assertFalse(StaffRegistrationRequest.objects.exists())

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

    def _submit_staff_request(
        self, national_code, mobile_number, center_id="CENTER-1"
    ):
        return self.client.post(
            "/api/auth/register/staff/",
            {
                "first_name": "Reza",
                "last_name": "Sadeghi",
                "national_code": national_code,
                "mobile_number": mobile_number,
                "center_id": center_id,
                "password": "Strong!Pass123",
            },
            format="json",
        )

    def test_center_admin_can_list_own_center_pending_requests(self):
        center = create_medical_center(center_id="CENTER-1")
        other_center = create_medical_center(center_id="CENTER-2")
        create_center_admin(center, username="admin-1")
        create_center_admin(other_center, username="admin-2")

        self._submit_staff_request(
            national_code="1111111111", mobile_number="09120000001"
        )
        self._submit_staff_request(
            national_code="2222222222",
            mobile_number="09120000002",
            center_id="CENTER-2",
        )

        admin = User.objects.get(username="admin-1")
        self.client.force_authenticate(user=admin)
        response = self.client.get("/api/staff-registration-requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["national_code"], "1111111111")

    def test_center_admin_can_accept_request(self):
        center = create_medical_center(center_id="CENTER-1")
        admin_profile = create_center_admin(center, username="admin-1")
        self._submit_staff_request(
            national_code="3333333333", mobile_number="09120000003"
        )
        registration_request = StaffRegistrationRequest.objects.get(
            national_code="3333333333"
        )

        self.client.force_authenticate(user=admin_profile.user)
        response = self.client.post(
            f"/api/staff-registration-requests/{registration_request.pk}/accept/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            User.objects.filter(
                username="3333333333", role=UserRole.MEDICAL_STAFF
            ).exists()
        )
        self.assertTrue(
            MedicalStaffProfile.objects.filter(
                national_code="3333333333", medical_center=center
            ).exists()
        )
        self.assertFalse(
            StaffRegistrationRequest.objects.filter(
                national_code="3333333333"
            ).exists()
        )

    def test_center_admin_can_reject_request(self):
        center = create_medical_center(center_id="CENTER-1")
        admin_profile = create_center_admin(center, username="admin-1")
        self._submit_staff_request(
            national_code="4444444444", mobile_number="09120000004"
        )
        registration_request = StaffRegistrationRequest.objects.get(
            national_code="4444444444"
        )

        self.client.force_authenticate(user=admin_profile.user)
        response = self.client.post(
            f"/api/staff-registration-requests/{registration_request.pk}/reject/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            StaffRegistrationRequest.objects.filter(
                national_code="4444444444"
            ).exists()
        )
        self.assertFalse(User.objects.filter(username="4444444444").exists())

    def test_center_admin_cannot_act_on_other_centers_request(self):
        my_center = create_medical_center(center_id="CENTER-1")
        other_center = create_medical_center(center_id="CENTER-2")
        admin_profile = create_center_admin(my_center, username="admin-1")
        self._submit_staff_request(
            national_code="5555555555",
            mobile_number="09120000005",
            center_id="CENTER-2",
        )
        other_request = StaffRegistrationRequest.objects.get(
            national_code="5555555555"
        )

        self.client.force_authenticate(user=admin_profile.user)
        response = self.client.post(
            f"/api/staff-registration-requests/{other_request.pk}/accept/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            StaffRegistrationRequest.objects.filter(
                national_code="5555555555"
            ).exists()
        )

    def test_non_admin_cannot_list_or_act_on_requests(self):
        center = create_medical_center(center_id="CENTER-1")
        self._submit_staff_request(
            national_code="6666666666", mobile_number="09120000006"
        )
        donor = User.objects.create_user(
            username="1234567890",
            password="Strong!Pass123",
            role=UserRole.DONOR,
        )

        self.client.force_authenticate(user=donor)
        response = self.client.get("/api/staff-registration-requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
