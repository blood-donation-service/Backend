import threading

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import (
    BloodGroup,
    DonorProfile,
    MedicalCenter,
    MedicalStaffProfile,
    User,
    UserRole,
)
from blood.models import (
    BloodRequest,
    Donation,
    DonationStatus,
    RequestStatus,
)
from blood.serializers import (
    BloodRequestCreateSerializer,
    BloodRequestSerializer,
    DonationStatusSerializer,
)

User = get_user_model()


def create_medical_center(center_id="CENTER-1", **overrides):
    defaults = {
        "name": "Sina Hospital",
        "postal_code": "1234567890",
        "address": "Tehran, Valiasr",
        "phone_number": "02112345678",
    }
    defaults.update(overrides)
    return MedicalCenter.objects.create(center_id=center_id, **defaults)


def create_medical_staff(center, username="staff-1"):
    user = User.objects.create_user(
        username=username,
        password="Strong!Pass123",
        role=UserRole.MEDICAL_STAFF,
    )
    seed = str(abs(hash(username)) % 10000000000).zfill(10)
    mobile = f"091{int(seed[-8:]) % 10000000:08d}"
    profile = MedicalStaffProfile.objects.create(
        user=user,
        medical_center=center,
        first_name="Sara",
        last_name="Karimi",
        national_code=seed,
        mobile_number=mobile,
    )
    return user, profile


def create_donor(username="donor-1"):
    user = User.objects.create_user(
        username=username,
        password="Strong!Pass123",
        role=UserRole.DONOR,
    )
    seed = str(abs(hash(username)) % 10000000000).zfill(10)
    mobile = f"091{int(seed[-8:]) % 10000000:08d}"
    profile = DonorProfile.objects.create(
        user=user,
        first_name="Ali",
        last_name="Rahimi",
        national_code=seed,
        mobile_number=mobile,
        blood_group="A+",
        province="Tehran",
    )
    return user, profile


def create_blood_request(center, **overrides):
    defaults = {
        "title": "Urgent A+ needed",
        "blood_group": "A+",
        "total_capacity": 5,
        "medical_center": center,
    }
    defaults.update(overrides)
    return BloodRequest.objects.create(**defaults)


class BloodModelTests(TestCase):
    def test_blood_request_sets_default_remaining_capacity(self):
        center = create_medical_center()
        request = create_blood_request(center)
        self.assertEqual(request.remaining_capacity, 5)

    def test_blood_request_clean_rejects_smaller_total_capacity(self):
        center = create_medical_center()
        request = create_blood_request(center, total_capacity=3)
        request.total_capacity = 2
        with self.assertRaises(Exception):
            request.save()

    def test_donation_requires_donation_date_when_marked_donated(self):
        center = create_medical_center()
        _, donor_profile = create_donor("donor-2")
        request = create_blood_request(center)
        donation = Donation(
            donor=donor_profile,
            request=request,
            status=DonationStatus.DONATED,
        )
        with self.assertRaises(Exception):
            donation.full_clean()


class BloodSerializerTests(TestCase):
    def test_blood_request_create_serializer_accepts_valid_data(self):
        serializer = BloodRequestCreateSerializer(
            data={"title": "Need A+", "blood_group": "A+", "total_capacity": 4}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_donation_status_serializer_only_allows_donated(self):
        serializer = DonationStatusSerializer(data={"status": "donated"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_blood_request_serializer_includes_nested_center(self):
        center = create_medical_center(center_id="CENTER-2")
        request = create_blood_request(center)
        serializer = BloodRequestSerializer(request)
        self.assertEqual(serializer.data["medical_center"]["center_id"], center.center_id)


class BloodViewTests(APITestCase):
    def test_list_view_returns_only_active_requests(self):
        center = create_medical_center(center_id="CENTER-3")
        create_blood_request(center, title="Open request")
        create_blood_request(center, title="Resolved request", status=RequestStatus.RESOLVED)
        response = self.client.get("/blood/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Open request")

    def test_medical_staff_can_create_request(self):
        center = create_medical_center(center_id="CENTER-4")
        user, _ = create_medical_staff(center, username="staff-2")
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/blood/requests/create/",
            {"title": "Need B+", "blood_group": "B+", "total_capacity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Need B+")
        self.assertEqual(BloodRequest.objects.count(), 1)

    def test_non_staff_cannot_create_request(self):
        user, _ = create_donor("donor-5")
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/blood/requests/create/",
            {"title": "Need B+", "blood_group": "B+", "total_capacity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_view_returns_404_for_missing_request(self):
        response = self.client.get("/blood/requests/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_donor_can_register_and_cancel_donation(self):
        center = create_medical_center(center_id="CENTER-5")
        request = create_blood_request(center, total_capacity=2)
        user, profile = create_donor("donor-3")
        self.client.force_authenticate(user=user)
        donate_response = self.client.post(f"/blood/requests/{request.pk}/donate/")
        self.assertEqual(donate_response.status_code, status.HTTP_201_CREATED)
        donation = Donation.objects.get(request=request, donor=profile)
        self.assertEqual(donation.status, DonationStatus.PENDING)
        self.assertEqual(BloodRequest.objects.get(pk=request.pk).remaining_capacity, 1)

        cancel_response = self.client.patch(f"/blood/donations/{donation.pk}/")
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Donation.objects.get(pk=donation.pk).status, DonationStatus.CANCELLED)
        self.assertEqual(BloodRequest.objects.get(pk=request.pk).remaining_capacity, 2)

    def test_non_donor_cannot_view_donations(self):
        user, _ = create_medical_staff(create_medical_center(center_id="CENTER-6"), username="staff-3")
        self.client.force_authenticate(user=user)
        response = self.client.get("/blood/donations/me/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancelling_non_pending_donation_returns_403_for_other_donor(self):
        center = create_medical_center(center_id="CENTER-7")
        _, donor_profile = create_donor("donor-4")
        request = create_blood_request(center)
        donation = Donation.objects.create(
            donor=donor_profile,
            request=request,
            status=DonationStatus.CANCELLED,
        )
        user, _ = create_donor("donor-6")
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/blood/donations/{donation.pk}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_medical_staff_can_mark_donation_as_donated(self):
        center = create_medical_center(center_id="CENTER-8")
        _, donor_profile = create_donor("donor-7")
        request = create_blood_request(center)
        donation = Donation.objects.create(donor=donor_profile, request=request)
        user, _ = create_medical_staff(center, username="staff-4")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/blood/donations/{donation.pk}/donated/",
            {"status": "donated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Donation.objects.get(pk=donation.pk).status, DonationStatus.DONATED)

    def test_staff_from_other_center_cannot_mark_donation(self):
        center = create_medical_center(center_id="CENTER-9")
        other_center = create_medical_center(center_id="CENTER-10")
        _, donor_profile = create_donor("donor-8")
        request = create_blood_request(center)
        donation = Donation.objects.create(donor=donor_profile, request=request)
        user, _ = create_medical_staff(other_center, username="staff-5")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/blood/donations/{donation.pk}/donated/",
            {"status": "donated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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

        self.donor1 = self._create_donor(
            "donor1",
            "2222222222",
            "09120000002",
        )

        self.donor2 = self._create_donor(
            "donor2",
            "3333333333",
            "09120000003",
        )

    def tearDown(self):
        connections.close_all()
        super().tearDown()

    def _create_donor(self, username, national_code, mobile):
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

    def _donate(self, user, request_pk, results):
        try:
            client = APIClient()
            client.force_authenticate(user=user)
            response = client.post(
                reverse("register-donation", kwargs={"pk": request_pk})
            )
            results.append(response.status_code)
        finally:
            connections.close_all()

    def test_race_condition(self):
        results = []
        request_pk = self.request.pk

        t1 = threading.Thread(
            target=self._donate,
            args=(self.donor1, request_pk, results),
        )
        t2 = threading.Thread(
            target=self._donate,
            args=(self.donor2, request_pk, results),
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        connections.close_all()

        self.request.refresh_from_db()

        self.assertEqual(
            len(results),
            2,
            f"Expected 2 responses, got {results}",
        )
        self.assertEqual(
            results.count(201),
            1,
            f"Expected exactly one 201, got {results}",
        )
        self.assertEqual(
            results.count(400),
            1,
            f"Expected exactly one 400, got {results}",
        )
        self.assertEqual(Donation.objects.count(), 1)
        self.assertEqual(self.request.remaining_capacity, 0)
        self.assertEqual(self.request.status, RequestStatus.PENDING)
