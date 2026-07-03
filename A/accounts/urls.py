from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/register/donor/", views.DonorRegisterView.as_view(), name="donor-register"),
    path(
        "auth/register/staff/",
        views.MedicalStaffRegisterView.as_view(),
        name="medical-staff-register",
    ),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("accounts/me/", views.AccountMeView.as_view(), name="account-me"),
]
