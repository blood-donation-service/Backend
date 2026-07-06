from .base import *
from datetime import timedelta

REST_FRAMEWORK = {

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',

    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

}

ACCESS_TOKEN_LIFETIME = env("ACCESS_TOKEN_LIFETIME", "00-00-01").split("-")
REFRESH_TOKEN_LIFETIME = env("REFRESH_TOKEN_LIFETIME", "00-00-10").split("-")

acces_kwargs = {
    "days": int(ACCESS_TOKEN_LIFETIME[0]),
    "hours": int(ACCESS_TOKEN_LIFETIME[1]),
    "minutes": int(ACCESS_TOKEN_LIFETIME[2]),
}

refresh_kwargs = {
    "days": int(REFRESH_TOKEN_LIFETIME[0]),
    "hours": int(REFRESH_TOKEN_LIFETIME[1]),
    "minutes": int(REFRESH_TOKEN_LIFETIME[2]),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(**acces_kwargs),
    "REFRESH_TOKEN_LIFETIME": timedelta(**refresh_kwargs),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Blood Donation API",
    "DESCRIPTION": (
        "REST API for the Blood Donation platform.\n\n"
        "## Authentication\n"
        "All protected endpoints expect a JWT access token in the "
        "`Authorization: Bearer <token>` header. Obtain tokens from "
        "`/api/auth/login/` and refresh them via `/api/auth/token/refresh/`.\n\n"
        "## Roles\n"
        "- **donor** — can register for blood requests and manage their own donations.\n"
        "- **medical_staff** — belongs to a medical center, can create / update / resolve "
        "blood requests and mark donations as donated.\n\n"
        "## Error format\n"
        "Errors are returned as `{\"detail\": \"...\"}` for permission/auth issues and "
        "as field-keyed maps for validation errors."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "auth", "description": "Registration, login, profile, medical centers."},
        {"name": "blood-requests", "description": "Public and staff blood request endpoints."},
        {"name": "donations", "description": "Donor and staff donation management."},
        {"name": "search", "description": "Search and filter blood requests."},
        {"name": "home", "description": "Health-check / homepage."},
    ],
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "BloodGroupEnum": "accounts.models.BloodGroup",
        "RequestStatusEnum": "blood.models.RequestStatus",
        "DonationStatusEnum": "blood.models.DonationStatus",
        "UserRoleEnum": "accounts.models.UserRole",
    },
    "SECURITY": [{"jwtAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT access token. Obtain from `/api/auth/login/`.",
            }
        }
    },
}
