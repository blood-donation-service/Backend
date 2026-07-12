import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from accounts.models import BloodGroup, DonorProfile, MedicalCenter
from blood.models import (
    BloodRequest,
    Donation,
    DonationStatus,
    RequestStatus,
)

fake = Faker("fa_IR")


COMPATIBLE_DONORS = {
    BloodGroup.O_NEGATIVE: [
        BloodGroup.O_NEGATIVE,
    ],
    BloodGroup.O_POSITIVE: [
        BloodGroup.O_NEGATIVE,
        BloodGroup.O_POSITIVE,
    ],
    BloodGroup.A_NEGATIVE: [
        BloodGroup.O_NEGATIVE,
        BloodGroup.A_NEGATIVE,
    ],
    BloodGroup.A_POSITIVE: [
        BloodGroup.O_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.A_POSITIVE,
    ],
    BloodGroup.B_NEGATIVE: [
        BloodGroup.O_NEGATIVE,
        BloodGroup.B_NEGATIVE,
    ],
    BloodGroup.B_POSITIVE: [
        BloodGroup.O_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.B_POSITIVE,
    ],
    BloodGroup.AB_NEGATIVE: [
        BloodGroup.O_NEGATIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.AB_NEGATIVE,
    ],
    BloodGroup.AB_POSITIVE: [
        bg[0] for bg in BloodGroup.choices
    ],
}



class Command(BaseCommand):
    help = "Generate BloodRequest and Donation fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "--requests-per-center",
            type=int,
            default=5,
            help="Number of blood requests per medical center.",
        )

        parser.add_argument(
            "--max-donations-per-request",
            type=int,
            default=15,
            help="Maximum donations generated for each request.",
        )

    def handle(self, *args, **options):
        requests_per_center = options["requests_per_center"]
        max_donations = options["max_donations_per_request"]

        centers = list(MedicalCenter.objects.all())

        if not centers:
            self.stdout.write(
                self.style.ERROR("No Medical Centers found.")
            )
            return

        titles = [
            "Emergency Surgery",
            "Trauma Patient",
            "ICU Patient",
            "Cancer Treatment",
            "Blood Bank Refill",
            "Scheduled Operation",
            "Urgent Blood Need",
            "Critical Patient",
            "Accident Victim",
            "Rare Blood Requirement",
        ]

        blood_groups = [bg[0] for bg in BloodGroup.choices]

        created_requests = 0
        created_donations = 0

        self.stdout.write("Creating Blood Requests...")

        for center in centers:

            for _ in range(requests_per_center):

                blood_group = random.choice(blood_groups)
                capacity = random.randint(5, 25)

                request = BloodRequest.objects.create(
                    medical_center=center,
                    title=random.choice(titles),
                    blood_group=blood_group,
                    total_capacity=capacity,
                    status=random.choices(
                        [
                            RequestStatus.ACTIVE,
                            RequestStatus.PENDING,
                            RequestStatus.RESOLVED,
                        ],
                        weights=[70, 20, 10],
                    )[0],
                )

                created_requests += 1

                compatible_groups = COMPATIBLE_DONORS[blood_group]

                matching_donors = list(
                    DonorProfile.objects.filter(
                        blood_group__in=compatible_groups
                    )
                )

                if not matching_donors:
                    continue

                random.shuffle(matching_donors)

                donation_count = random.randint(
                    0,
                    min(
                        max_donations,
                        capacity,
                        len(matching_donors),
                    ),
                )

                occupied_count = 0

                for donor in matching_donors[:donation_count]:

                    status = random.choices(
                        [
                            DonationStatus.PENDING,
                            DonationStatus.DONATED,
                            DonationStatus.CANCELLED,
                        ],
                        weights=[40, 45, 15],
                    )[0]

                    donation = Donation(
                        donor=donor,
                        request=request,
                        status=status,
                    )

                if status == DonationStatus.DONATED:
                    donation.donated_at = timezone.now()
                    occupied_count += 1

                elif status == DonationStatus.PENDING:
                    occupied_count += 1

                elif status == DonationStatus.CANCELLED:
                    donation.cancelled_at = timezone.now()

                    donation.save()
                    created_donations += 1

                request.remaining_capacity = max(
                    request.total_capacity - occupied_count,
                    0,
                )

                if occupied_count >= request.total_capacity:
                    request.status = RequestStatus.RESOLVED

                request.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"""
Created

Blood Requests : {created_requests}
Donations      : {created_donations}
"""
            )
        )