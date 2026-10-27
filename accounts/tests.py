from unittest.mock import patch

from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from config.testing import make_user


class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()  # the rate limits are kept in the cache

    def register(self, **extra):
        data = {"username": "sam", "password": "StrongPass123", "email": "sam@example.com"}
        data.update(extra)
        return self.client.post("/api/v1/auth/register/", data, format="json")

    def login(self, username="sam", password="StrongPass123"):
        return self.client.post("/api/v1/auth/login/", {"username": username, "password": password}, format="json")

    def test_register_creates_user_without_returning_password(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], "sam")
        self.assertNotIn("password", response.data)

    def test_register_same_username_twice_fails(self):
        self.register()
        response = self.register()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")

    def test_register_weak_password_fails(self):
        response = self.register(password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["error"]["fields"])

    def test_login_returns_tokens(self):
        self.register()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password_is_unauthorized(self):
        self.register()
        response = self.login(password="wrong")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "unauthorized")

    def test_refresh_gives_new_access_token(self):
        self.register()
        refresh = self.login().data["refresh"]
        response = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_me_needs_a_token(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "unauthorized")

    def test_me_with_token(self):
        self.register()
        token = self.login().data["access"]
        response = self.client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION="Bearer " + token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "sam")
        self.assertFalse(response.data["is_admin"])

    def test_me_shows_admin_flag(self):
        make_user("boss", staff=True)
        token = self.login("boss").data["access"]
        response = self.client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION="Bearer " + token)
        self.assertTrue(response.data["is_admin"])

    def test_too_many_login_attempts_are_stopped(self):
        self.register()
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "3/minute"}):
            responses = [self.login(password="wrong") for _ in range(5)]
        self.assertEqual([r.status_code for r in responses], [401, 401, 401, 429, 429])
        self.assertEqual(responses[3].data["error"]["code"], "too_many_requests")

    def test_too_many_registrations_are_stopped(self):
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"register": "2/hour"}):
            codes = [self.register(username="user%d" % i).status_code for i in range(4)]
        self.assertEqual(codes, [201, 201, 429, 429])
