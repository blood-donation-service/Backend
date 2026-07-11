from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import DonorProfile, MedicalCenter, MedicalStaffProfile, User, UserRole
from .models import BloodRequest, Donation, DonationStatus, RequestStatus
from .serializers import BloodRequestCreateSerializer, BloodRequestSerializer, DonationSerializer, DonationStatusSerializer


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
    user = User.objects.create_user(username=username, password="Strong!Pass123", role=UserRole.MEDICAL_STAFF)
    profile = MedicalStaffProfile.objects.create(
        user=user,
        medical_center=center,
        first_name="Sara",
        last_name="Karimi",
        national_code="1111111111",
        mobile_number="09120000001",
    )
    return user, profile


def create_donor(username="donor-1"):
    user = User.objects.create_user(username=username, password="Strong!Pass123", role=UserRole.DONOR)
    profile = DonorProfile.objects.create(
        user=user,
        first_name="Ali",
        last_name="Rahimi",
        national_code="1234567890" if username == "donor-1" else "2345678901",
        mobile_number="09120000002" if username == "donor-1" else "09120000003",
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
        donation = Donation(donor=donor_profile, request=request, status=DonationStatus.DONATED)
        with self.assertRaises(Exception):
            donation.full_clean()


class BloodSerializerTests(TestCase):
    def test_blood_request_create_serializer_accepts_valid_data(self):
        serializer = BloodRequestCreateSerializer(data={"title": "Need A+", "blood_group": "A+", "total_capacity": 4})
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

    def test_medical_staff_can_mark_donation_as_donated(self):
        center = create_medical_center(center_id="CENTER-6")
        _, donor_profile = create_donor("donor-4")
        request = create_blood_request(center)
        donation = Donation.objects.create(donor=donor_profile, request=request)
        user, _ = create_medical_staff(center, username="staff-3")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/blood/donations/{donation.pk}/donated/",
            {"status": "donated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Donation.objects.get(pk=donation.pk).status, DonationStatus.DONATED)
