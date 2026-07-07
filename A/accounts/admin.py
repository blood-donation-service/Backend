from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    DonorProfile,
    MedicalCenter,
    MedicalCenterAdminProfile,
    MedicalStaffProfile,
    StaffRegistrationRequest,
    User,
    UserRole,
)


def _admin_center_qs(request):
    return MedicalCenter.objects.filter(admin_profile__user=request.user)


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

    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(MedicalCenter)
class MedicalCenterAdmin(admin.ModelAdmin):
    list_display = ("name", "center_id", "phone_number", "postal_code")
    search_fields = ("name", "center_id", "phone_number", "postal_code", "address")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(admin_profile__user=request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.pk).exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(MedicalStaffProfile)
class MedicalStaffProfileAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "medical_center",
    )
    list_filter = ("medical_center",)
    search_fields = (
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "medical_center__name",
        "medical_center__center_id",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(medical_center__admin_profile__user=request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.medical_center_id).exists()

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.medical_center_id).exists()


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

    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(MedicalCenterAdminProfile)
class MedicalCenterAdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "medical_center", "created_at")
    list_filter = ("medical_center",)
    search_fields = (
        "user__username",
        "medical_center__name",
        "medical_center__center_id",
    )

    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(StaffRegistrationRequest)
class StaffRegistrationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "medical_center",
        "status",
        "created_at",
    )
    list_filter = ("status", "medical_center")
    search_fields = (
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "medical_center__name",
        "medical_center__center_id",
    )
    readonly_fields = ("password_hash", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(medical_center__admin_profile__user=request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.medical_center_id).exists()

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.medical_center_id).exists()
