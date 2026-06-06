from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import DonorProfile, MedicalCenterProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Project role", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Project role", {"fields": ("role",)}),
    )
    list_display = ("username", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")


@admin.register(MedicalCenterProfile)
class MedicalCenterProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "center_id", "phone_number", "postal_code")
    search_fields = ("name", "center_id", "phone_number", "postal_code", "address")


@admin.register(DonorProfile)
class DonorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "blood_group",
        "province",
    )
    list_filter = ("blood_group", "province")
    search_fields = ("first_name", "last_name", "national_code", "mobile_number")
