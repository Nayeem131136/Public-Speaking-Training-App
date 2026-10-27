from django.test import TestCase


class JsonErrorTests(TestCase):
    def test_unknown_api_address_gives_json(self):
        response = self.client.get("/api/v1/nothing-here/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_server_error_gives_json_on_api_addresses(self):
        from django.test import RequestFactory

        from config.views import server_error

        response = server_error(RequestFactory().get("/api/v1/recordings/"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b'{"error": {"code": "server_error", "message": "Something went wrong on the server."}}')

    def test_other_addresses_keep_the_normal_page(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("application/json", response["Content-Type"])
