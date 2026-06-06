from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/register/donor/", views.DonorRegisterView.as_view(), name="donor-register"),
    path(
        "auth/register/center/",
        views.MedicalCenterRegisterView.as_view(),
        name="medical-center-register",
    ),
    path(
        "auth/centers/lookup/",
        views.MedicalCenterLookupView.as_view(),
        name="medical-center-lookup",
    ),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("accounts/me/", views.AccountMeView.as_view(), name="account-me"),
]
