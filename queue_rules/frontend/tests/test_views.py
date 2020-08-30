from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class TestHome(TestCase):
    def test_unauthenticated(self):
        client = Client()

        response = client.get(reverse("frontend-index"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Login with Spotify", response.content)

    def test_authenticated(self):
        test_user = User.objects.create(username="test")
        client = Client()
        client.force_login(test_user)

        response = client.get(reverse("frontend-index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Login with Spotify", response.content)
