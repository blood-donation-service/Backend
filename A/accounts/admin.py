from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field

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


class UserResource(resources.ModelResource):
    role = Field(column_name="role")

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
        )
        export_order = fields
        import_id_fields = ("username",)

    def before_import_row(self, row, **kwargs):
        if "password" in row and row["password"]:
            row["password"] = row["password"]


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ImportExportModelAdmin):
    resource_class = UserResource
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Project role", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Project role", {"fields": ("role",)}),
    )
    list_display = ("id", "username", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")

    def has_module_permission(self, request):
        return request.user.is_superuser


class MedicalCenterResource(resources.ModelResource):
    class Meta:
        model = MedicalCenter
        fields = (
            "id",
            "center_id",
            "name",
            "postal_code",
            "address",
            "phone_number",
            "province",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        )
        export_order = fields
        import_id_fields = ("center_id",)


@admin.register(MedicalCenter)
class MedicalCenterAdmin(ImportExportModelAdmin):
    resource_class = MedicalCenterResource
    list_display = ("id", "name", "center_id", "phone_number", "postal_code")
    search_fields = ("name", "center_id", "phone_number",
                     "postal_code", "address")

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


class MedicalStaffProfileResource(resources.ModelResource):
    class Meta:
        model = MedicalStaffProfile
        fields = (
            "id",
            "user__username",
            "medical_center__center_id",
            "first_name",
            "last_name",
            "national_code",
            "mobile_number",
            "created_at",
            "updated_at",
        )
        export_order = fields
        import_id_fields = ("national_code",)


@admin.register(MedicalStaffProfile)
class MedicalStaffProfileAdmin(ImportExportModelAdmin):
    resource_class = MedicalStaffProfileResource
    list_display = (
        "id",
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


class DonorProfileResource(resources.ModelResource):
    class Meta:
        model = DonorProfile
        fields = (
            "id",
            "user__username",
            "first_name",
            "last_name",
            "national_code",
            "mobile_number",
            "blood_group",
            "province",
            "created_at",
            "updated_at",
        )
        export_order = fields
        import_id_fields = ("national_code",)


@admin.register(DonorProfile)
class DonorProfileAdmin(ImportExportModelAdmin):
    resource_class = DonorProfileResource
    list_display = (
        "id",
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "blood_group",
        "province",
    )
    list_filter = ("blood_group", "province")
    search_fields = ("first_name", "last_name",
                     "national_code", "mobile_number")

    def has_module_permission(self, request):
        return request.user.is_superuser


class MedicalCenterAdminProfileResource(resources.ModelResource):
    class Meta:
        model = MedicalCenterAdminProfile
        fields = (
            "id",
            "user__username",
            "medical_center__center_id",
            "first_name",
            "last_name",
            "national_code",
            "mobile_number",
            "created_at",
            "updated_at",
        )
        export_order = fields
        import_id_fields = ("national_code",)


@admin.register(MedicalCenterAdminProfile)
class MedicalCenterAdminProfileAdmin(ImportExportModelAdmin):
    resource_class = MedicalCenterAdminProfileResource
    list_display = (
        "id",
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "medical_center",
        "user",
    )

    search_fields = (
        "first_name",
        "last_name",
        "national_code",
        "mobile_number",
        "user__username",
        "medical_center__name",
    )

    list_filter = ("medical_center",)
    autocomplete_fields = ("user", "medical_center")

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class StaffRegistrationRequestResource(resources.ModelResource):
    class Meta:
        model = StaffRegistrationRequest
        fields = (
            "id",
            "medical_center__center_id",
            "first_name",
            "last_name",
            "national_code",
            "mobile_number",
            "status",
            "created_at",
            "updated_at",
        )
        export_order = fields


@admin.register(StaffRegistrationRequest)
class StaffRegistrationRequestAdmin(ImportExportModelAdmin):
    resource_class = StaffRegistrationRequestResource
    list_display = (
        "id",
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
            self.message_user(
                request, f"Rejected registration for {full_name}.")
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
