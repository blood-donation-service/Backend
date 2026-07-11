from rest_framework import status
from rest_framework.test import APITestCase


class HomeViewTests(APITestCase):
    def test_home_endpoint_returns_service_name(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "blood-donation-api")
