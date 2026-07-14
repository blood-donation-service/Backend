import threading

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    BloodGroup,
    DonorProfile,
    MedicalCenter,
    MedicalStaffProfile,
    UserRole,
)
from blood.models import (
    BloodRequest,
    Donation,
    RequestStatus,
)

User = get_user_model()


class RegisterDonationRaceConditionTest(TransactionTestCase):
    reset_sequences = True
    serialized_rollback = True

    def setUp(self):
        self.center = MedicalCenter.objects.create(
            center_id="MC001",
            name="Test Hospital",
            postal_code="1234567890",
            address="Tehran",
            phone_number="+989121111111",
            province="Tehran",
        )

        staff = User.objects.create_user(
            username="staff",
            password="password123",
            role=UserRole.MEDICAL_STAFF,
        )

        MedicalStaffProfile.objects.create(
            user=staff,
            medical_center=self.center,
            first_name="Ali",
            last_name="Ahmadi",
            national_code="1111111111",
            mobile_number="09120000001",
        )

        self.request = BloodRequest.objects.create(
            medical_center=self.center,
            title="Need Blood",
            blood_group=BloodGroup.A_POSITIVE,
            total_capacity=1,
        )

        self.donor1 = self.create_donor(
            "donor1",
            "2222222222",
            "09120000002",
        )

        self.donor2 = self.create_donor(
            "donor2",
            "3333333333",
            "09120000003",
        )

    def tearDown(self):
        connections.close_all()
        super().tearDown()

    def create_donor(self, username, national_code, mobile):
        user = User.objects.create_user(
            username=username,
            password="password123",
            role=UserRole.DONOR,
        )

        DonorProfile.objects.create(
            user=user,
            first_name=username,
            last_name="Test",
            national_code=national_code,
            mobile_number=mobile,
            blood_group=BloodGroup.A_POSITIVE,
            province="Tehran",
        )

        return user

    def donate(self, user, results):
        try:
            client = APIClient()
            client.force_authenticate(user=user)

            response = client.post(
                reverse(
                    "register-donation",
                    kwargs={"pk": self.request.pk},
                )
            )

            results.append(response.status_code)
        finally:
            connections.close_all()

    def test_race_condition(self):
        results = []

        t1 = threading.Thread(
            target=self.donate,
            args=(self.donor1, results),
        )

        t2 = threading.Thread(
            target=self.donate,
            args=(self.donor2, results),
        )

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        connections.close_all()

        self.request.refresh_from_db()

        self.assertEqual(
            Donation.objects.count(),
            1,
        )

        self.assertEqual(
            self.request.remaining_capacity,
            0,
        )

        self.assertEqual(
            self.request.status,
            RequestStatus.PENDING,
        )

        self.assertEqual(
            results.count(201),
            1,
        )

        self.assertEqual(
            results.count(400),
            1,
        )