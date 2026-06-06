from django.contrib import admin

from .models import BloodRequest, Donation


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "medical_center",
        "blood_group",
        "total_capacity",
        "remaining_capacity",
        "status",
        "created_at",
    )
    list_filter = ("status", "blood_group", "created_at")
    search_fields = ("title", "medical_center__name", "medical_center__center_id")


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("donor", "request", "status", "registered_at", "donated_at")
    list_filter = ("status", "registered_at", "donated_at")
    search_fields = (
        "donor__first_name",
        "donor__last_name",
        "donor__national_code",
        "request__title",
        "request__medical_center__name",
    )
