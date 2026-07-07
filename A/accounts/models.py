from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class UserRole(models.TextChoices):
    DONOR = "donor", "Donor"
    MEDICAL_STAFF = "medical_staff", "Medical staff"
    CENTER_ADMIN="admin","Admin"


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


class MedicalCenter(models.Model):
    center_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    postal_code = models.CharField(
        max_length=10,
        validators=[postal_code_validator],
        db_index=True,
    )
    address = models.TextField()
    phone_number = models.CharField(
        max_length=16, validators=[phone_validator])
    province = models.CharField(
        max_length=100, db_index=True, default="Tehran")
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

    def __str__(self):
        return f"{self.name} ({self.center_id})"


class MedicalStaffProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="medical_staff_profile",
    )
    medical_center = models.ForeignKey(
        MedicalCenter,
        on_delete=models.CASCADE,
        related_name="staff",
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != UserRole.MEDICAL_STAFF:
            raise ValidationError(
                {"user": "Medical staff profile must belong to a medical staff user."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.national_code})"


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
            raise ValidationError(
                {"user": "Donor profile must belong to a donor user."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.national_code})"


class MedicalCenterAdminProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="center_admin_profile",
    )
    medical_center = models.OneToOneField(
        MedicalCenter,
        on_delete=models.CASCADE,
        related_name="admin_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != UserRole.CENTER_ADMIN:
            raise ValidationError(
                {"user": "Medical center admin profile must belong to a center admin user."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} -> {self.medical_center.name}"


class StaffRegistrationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class StaffRegistrationRequest(models.Model):
    medical_center = models.ForeignKey(
        MedicalCenter,
        on_delete=models.CASCADE,
        related_name="staff_registration_requests",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    national_code = models.CharField(
        max_length=10,
        validators=[national_code_validator],
        db_index=True,
    )
    mobile_number = models.CharField(
        max_length=11,
        validators=[mobile_validator],
    )
    password_hash = models.CharField(max_length=256)
    status = models.CharField(
        max_length=16,
        choices=StaffRegistrationStatus.choices,
        default=StaffRegistrationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["national_code"],
                condition=models.Q(status="pending"),
                name="unique_pending_staff_request_national_code",
            ),
            models.UniqueConstraint(
                fields=["mobile_number"],
                condition=models.Q(status="pending"),
                name="unique_pending_staff_request_mobile_number",
            ),
        ]

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def __str__(self):
        return f"{self.first_name} {self.last_name} -> {self.medical_center.name} ({self.status})"
