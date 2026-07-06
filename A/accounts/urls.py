from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

_token_refresh_schema = extend_schema(
    tags=["auth"],
    summary="Refresh JWT access token",
    description="Exchange a valid refresh token for a new access token.",
    request={"application/json": {"type": "object", "properties": {
        "refresh": {"type": "string", "description": "Valid JWT refresh token."}
    }, "required": ["refresh"]}},
    responses={
        200: {"type": "object", "properties": {
            "access": {"type": "string"}
        }},
        401: {"description": "Refresh token is invalid or expired."},
    },
    auth=[],
)


@_token_refresh_schema
class _TokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


urlpatterns = [
    path("auth/register/donor/",
         views.DonorRegisterView.as_view(), name="donor-register"),
    path(
        "auth/register/staff/",
        views.MedicalStaffRegisterView.as_view(),
        name="medical-staff-register",
    ),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", _TokenRefreshView.as_view(), name="token-refresh"),
    path("accounts/me/", views.AccountMeView.as_view(), name="account-me"),
    path("auth/centers/", views.MedicalCenterListView.as_view(), name="centers"),
]
