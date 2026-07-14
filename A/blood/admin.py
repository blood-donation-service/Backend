from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import BloodRequest, Donation


class BloodRequestResource(resources.ModelResource):
    class Meta:
        model = BloodRequest
        fields = (
            "id",
            "medical_center__center_id",
            "title",
            "blood_group",
            "total_capacity",
            "remaining_capacity",
            "status",
            "created_at",
            "updated_at",
        )
        export_order = fields


@admin.register(BloodRequest)
class BloodRequestAdmin(ImportExportModelAdmin):
    resource_class = BloodRequestResource
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


class DonationResource(resources.ModelResource):
    class Meta:
        model = Donation
        fields = (
            "id",
            "donor__national_code",
            "request__title",
            "status",
            "registered_at",
            "donated_at",
            "cancelled_at",
            "updated_at",
        )
        export_order = fields


@admin.register(Donation)
class DonationAdmin(ImportExportModelAdmin):
    resource_class = DonationResource
    list_display = ("donor", "request", "status", "registered_at", "donated_at")
    list_filter = ("status", "registered_at", "donated_at")
    search_fields = (
        "donor__first_name",
        "donor__last_name",
        "donor__national_code",
        "request__title",
        "request__medical_center__name",
    )
