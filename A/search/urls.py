from django.urls import path

from .views import BloodRequestSearchView

urlpatterns = [
    path(
        "blood-requests/",
        BloodRequestSearchView.as_view(),
        name="blood-request-search",
    ),
]