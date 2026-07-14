import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker

from accounts.models import (
    MedicalCenter,
    MedicalCenterAdminProfile,
    MedicalStaffProfile,
    DonorProfile,
    UserRole,
    BloodGroup,
)

from django.contrib.auth.hashers import make_password

PASSWORD = make_password("123456")

fake = Faker("fa_IR")
User = get_user_model()


class Command(BaseCommand):
    help = "Generate fixture data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--centers",
            type=int,
            default=5,
            help="Number of medical centers",
        )

        parser.add_argument(
            "--staff-per-center",
            type=int,
            default=3,
            help="Medical staff per center",
        )

        parser.add_argument(
            "--donors",
            type=int,
            default=100,
            help="Number of donors",
        )

    def handle(self, *args, **options):

        centers = options["centers"]
        staff_per_center = options["staff_per_center"]
        donors = options["donors"]

        self.stdout.write("Creating Medical Centers...")

        created_centers = []

        for i in range(centers):

            center = MedicalCenter.objects.create(
                center_id=f"CENTER-{i+1:04}",
                name=f"Medical Center {i+1}",
                postal_code=f"{1000000000+i}",
                address=fake.address(),
                phone_number=f"+989120000{i:04}",
                province=random.choice(
                    [
                        "Tehran",
                        "Isfahan",
                        "Shiraz",
                        "Mashhad",
                        "Tabriz",
                    ]
                ),
                latitude=35.7 + random.random(),
                longitude=51.3 + random.random(),
            )

            created_centers.append(center)

            admin_user = User.objects.create(
                username=f"admin{i+1}",
                password=PASSWORD,
                role=UserRole.CENTER_ADMIN,
                is_staff=True,
            )

            MedicalCenterAdminProfile.objects.create(
                user=admin_user,
                medical_center=center,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                national_code=f"{3000000000+i}",
                mobile_number=f"09{900000000+i:09}",
            )

            for j in range(staff_per_center):

                index = i * staff_per_center + j

                staff_user = User.objects.create(
                    username=f"staff{index+1}",
                    password=PASSWORD,
                    role=UserRole.MEDICAL_STAFF,
                )

                MedicalStaffProfile.objects.create(
                    user=staff_user,
                    medical_center=center,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    national_code=f"{4000000000+index}",
                    mobile_number=f"09{910000000+index:09}",
                )

        self.stdout.write("Creating Donors...")

        blood_groups = [bg[0] for bg in BloodGroup.choices]

        provinces = [
            "Tehran",
            "Mashhad",
            "Shiraz",
            "Isfahan",
            "Tabriz",
        ]

        for i in range(donors):

            donor_user = User.objects.create(
                username=f"donor{i+1}",
                password=PASSWORD,
                role=UserRole.DONOR,
            )

            DonorProfile.objects.create(
                user=donor_user,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                national_code=f"{5000000000+i}",
                mobile_number=f"09{920000000+i:09}",
                blood_group=random.choice(blood_groups),
                province=random.choice(provinces),
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"""
Created

Medical Centers : {centers}
Admins          : {centers}
Medical Staff   : {centers * staff_per_center}
Donors          : {donors}

Password for every user: 123456
"""
            )
        )
