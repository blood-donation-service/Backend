from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    DonorProfile,
    MedicalCenter,
    MedicalCenterAdminProfile,
    MedicalStaffProfile,
    StaffRegistrationRequest,
    StaffRegistrationStatus,
    User,
    UserRole,
)


def _is_center_admin(user):
    return (
        user.is_authenticated
        and user.role == UserRole.CENTER_ADMIN
        and hasattr(user, "center_admin_profile")
    )


def _admin_center_qs(request):
    return MedicalCenter.objects.filter(admin_profile__user=request.user)


def _can_see_module(request):
    return request.user.is_superuser or _is_center_admin(request.user)


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

    def has_module_permission(self, request):
        return _can_see_module(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.pk).exists()

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

    def has_module_permission(self, request):
        return _can_see_module(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.medical_center_id).exists()

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
    actions = ["accept_selected", "reject_selected"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(medical_center__admin_profile__user=request.user)

    def has_module_permission(self, request):
        return _can_see_module(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return _admin_center_qs(request).filter(pk=obj.medical_center_id).exists()

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

    def save_model(self, request, obj, form, change):
        new_status = obj.status
        old_status = (
            StaffRegistrationRequest.objects.get(pk=obj.pk).status
            if change and obj.pk
            else None
        )

        if (
            change
            and old_status == StaffRegistrationStatus.PENDING
            and new_status == StaffRegistrationStatus.APPROVED
        ):
            if not self.has_delete_permission(request, obj):
                self.message_user(
                    request,
                    "You can only approve requests for your own medical center.",
                    level="error",
                )
                return
            from .views import _approve_registration_request  # avoid import cycle

            full_name = f"{obj.first_name} {obj.last_name}"
            user = _approve_registration_request(obj)
            if user is None:
                self.message_user(
                    request,
                    f"Could not approve registration for {full_name}: "
                    f"the request is no longer pending.",
                    level="error",
                )
                return
            self.message_user(
                request,
                f"Approved registration for {full_name}. "
                f"User and medical staff profile created.",
            )
            return

        if (
            change
            and old_status == StaffRegistrationStatus.PENDING
            and new_status == StaffRegistrationStatus.REJECTED
        ):
            if not self.has_delete_permission(request, obj):
                self.message_user(
                    request,
                    "You can only reject requests for your own medical center.",
                    level="error",
                )
                return
            full_name = f"{obj.first_name} {obj.last_name}"
            obj.delete()
            self.message_user(request, f"Rejected registration for {full_name}.")
            return

        super().save_model(request, obj, form, change)

    @admin.action(description="Accept selected registration requests")
    def accept_selected(self, request, queryset):
        from .views import _approve_registration_request  # local import to avoid cycle

        accepted = 0
        skipped = 0
        for registration_request in queryset.filter(
            status=StaffRegistrationStatus.PENDING
        ):
            if not self.has_delete_permission(request, registration_request):
                skipped += 1
                continue
            _approve_registration_request(registration_request)
            accepted += 1
        if accepted:
            self.message_user(request, f"Accepted {accepted} request(s).")
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} request(s) (not pending or not in your center).",
            )

    @admin.action(description="Reject selected registration requests")
    def reject_selected(self, request, queryset):
        rejected = 0
        for registration_request in queryset.filter(
            status=StaffRegistrationStatus.PENDING
        ):
            if not self.has_delete_permission(request, registration_request):
                continue
            registration_request.delete()
            rejected += 1
        if rejected:
            self.message_user(request, f"Rejected {rejected} request(s).")
