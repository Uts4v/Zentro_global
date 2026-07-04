from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class RoleAwareLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_customer_login_rejects_merchant_role_request(self):
        user = User.objects.create_user(
            username="customer1",
            email="customer@example.com",
            password="StrongPass123!",
            role="customer",
        )

        response = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "StrongPass123!", "role": "merchant"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("customer", str(response.data).lower())

    def test_merchant_login_rejects_customer_role_request(self):
        user = User.objects.create_user(
            username="merchant1",
            email="merchant@example.com",
            password="StrongPass123!",
            role="merchant",
        )

        response = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "StrongPass123!", "role": "customer"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("merchant", str(response.data).lower())
