from rest_framework.permissions import BasePermission

from .models import UserRole


class IsDonor(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.DONOR
        )


class IsMedicalStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.MEDICAL_STAFF
        )


class IsCenterAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == UserRole.CENTER_ADMIN):
            return False
        return getattr(user, "center_admin_profile", None) is not None
