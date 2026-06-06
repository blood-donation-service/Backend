from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class UserRole(models.TextChoices):
    DONOR = "donor", "Donor"
    MEDICAL_CENTER = "medical_center", "Medical center"


class User(AbstractUser):
    role = models.CharField(max_length=32, choices=UserRole.choices)

    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class BloodGroup(models.TextChoices):
    A_POSITIVE = "A+", "A+"
    A_NEGATIVE = "A-", "A-"
    B_POSITIVE = "B+", "B+"
    B_NEGATIVE = "B-", "B-"
    AB_POSITIVE = "AB+", "AB+"
    AB_NEGATIVE = "AB-", "AB-"
    O_POSITIVE = "O+", "O+"
    O_NEGATIVE = "O-", "O-"


phone_validator = RegexValidator(
    regex=r"^\+?\d{10,15}$",
    message="Enter a valid phone number with 10 to 15 digits.",
)
mobile_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="Enter a valid Iranian mobile number.",
)
national_code_validator = RegexValidator(
    regex=r"^\d{10}$",
    message="National code must contain exactly 10 digits.",
)
postal_code_validator = RegexValidator(
    regex=r"^\d{10}$",
    message="Postal code must contain exactly 10 digits.",
)


class MedicalCenterProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="medical_center_profile",
    )
    center_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    postal_code = models.CharField(
        max_length=10,
        validators=[postal_code_validator],
        db_index=True,
    )
    address = models.TextField()
    phone_number = models.CharField(max_length=16, validators=[phone_validator])
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != UserRole.MEDICAL_CENTER:
            raise ValidationError(
                {"user": "Medical center profile must belong to a medical center user."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.center_id})"


class DonorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="donor_profile",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    national_code = models.CharField(
        max_length=10,
        unique=True,
        validators=[national_code_validator],
        db_index=True,
    )
    mobile_number = models.CharField(
        max_length=11,
        unique=True,
        validators=[mobile_validator],
    )
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices)
    province = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != UserRole.DONOR:
            raise ValidationError({"user": "Donor profile must belong to a donor user."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.national_code})"
