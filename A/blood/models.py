from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from accounts.models import BloodGroup, DonorProfile, MedicalCenter


class RequestStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PENDING = "pending", "Pending"
    RESOLVED = "resolved", "Resolved"


class DonationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DONATED = "donated", "Donated"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class BloodRequest(models.Model):
    medical_center = models.ForeignKey(
        MedicalCenter,
        on_delete=models.CASCADE,
        related_name="blood_requests",
    )
    title = models.CharField(max_length=255)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices)
    total_capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)])
    remaining_capacity = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=RequestStatus.choices,
        default=RequestStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "blood_group"]),
            models.Index(fields=["created_at"]),
        ]

    def clean(self):
        super().clean()
        if self.remaining_capacity > self.total_capacity:
            raise ValidationError(
                {"remaining_capacity": "Remaining capacity cannot exceed total capacity."}
            )
        if not self.pk:
            return

        previous = BloodRequest.objects.only("blood_group", "total_capacity").get(
            pk=self.pk
        )
        if self.blood_group != previous.blood_group:
            raise ValidationError(
                {"blood_group": "Blood group cannot be changed."})
        if self.total_capacity < previous.total_capacity:
            raise ValidationError(
                {"total_capacity": "Total capacity cannot be decreased."}
            )

    def save(self, *args, **kwargs):
        if self._state.adding and self.remaining_capacity == 0:
            self.remaining_capacity = self.total_capacity
        elif self.pk:
            previous = BloodRequest.objects.only(
                "total_capacity",
                "remaining_capacity",
            ).get(pk=self.pk)
            if (
                self.total_capacity > previous.total_capacity
                and self.remaining_capacity == previous.remaining_capacity
            ):
                self.remaining_capacity += self.total_capacity - previous.total_capacity

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.blood_group} ({self.remaining_capacity}/{self.total_capacity})"


class Donation(models.Model):
    donor = models.ForeignKey(
        DonorProfile,
        on_delete=models.CASCADE,
        related_name="donations",
    )
    request = models.ForeignKey(
        BloodRequest,
        on_delete=models.CASCADE,
        related_name="donations",
    )
    status = models.CharField(
        max_length=16,
        choices=DonationStatus.choices,
        default=DonationStatus.PENDING,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    donated_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-registered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["donor", "request"],
                condition=Q(
                    status__in=[DonationStatus.PENDING, DonationStatus.DONATED]),
                name="unique_active_donation_per_request",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "registered_at"]),
            models.Index(fields=["donated_at"]),
        ]

    def clean(self):
        super().clean()
        if self.status == DonationStatus.DONATED and self.donated_at is None:
            raise ValidationError({"donated_at": "Donation date is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.donor} -> {self.request} ({self.get_status_display()})"
