from appconfig.defaults import DEFAULTS
from appconfig.models import AppSetting
from config.testing import ApiTestCase, client_for, make_user


class SettingsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.admin = client_for(make_user("boss", staff=True))

    def test_needs_login(self):
        self.assertEqual(self.client.get("/api/v1/settings/").status_code, 401)

    def test_defaults_are_returned_when_the_database_is_empty(self):
        response = self.api.get("/api/v1/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, DEFAULTS)

    def test_admin_changes_a_value_and_everyone_sees_it(self):
        response = self.admin.patch("/api/v1/settings/wpm_target_max/", {"value": 170}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"key": "wpm_target_max", "value": 170})
        self.assertEqual(self.api.get("/api/v1/settings/").data["wpm_target_max"], 170)
        # changing it again updates the same row
        self.admin.patch("/api/v1/settings/wpm_target_max/", {"value": 180}, format="json")
        self.assertEqual(AppSetting.objects.filter(key="wpm_target_max").count(), 1)

    def test_normal_user_cannot_change_a_value(self):
        response = self.api.patch("/api/v1/settings/wpm_target_max/", {"value": 170}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "forbidden")

    def test_not_logged_in_cannot_change_a_value(self):
        response = self.client.patch("/api/v1/settings/wpm_target_max/", {"value": 170}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_unknown_key(self):
        response = self.admin.patch("/api/v1/settings/nope/", {"value": 1}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_value_is_required(self):
        response = self.admin.patch("/api/v1/settings/wpm_target_max/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_wrong_kinds_of_values_are_rejected(self):
        bad = [("wpm_target_max", "fast"), ("wpm_target_max", -5), ("wpm_target_max", 0), ("wpm_target_max", True),
               ("whisper_model", 3), ("whisper_model", "huge"), ("default_language", "fr")]
        for key, value in bad:
            response = self.admin.patch("/api/v1/settings/%s/" % key, {"value": value}, format="json")
            self.assertEqual(response.status_code, 400, (key, value))

    def test_text_settings_accept_valid_choices(self):
        response = self.admin.patch("/api/v1/settings/whisper_model/", {"value": "small"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_a_changed_setting_is_used_by_the_pipeline(self):
        self.admin.patch("/api/v1/settings/wpm_target_min/", {"value": 10}, format="json")
        self.admin.patch("/api/v1/settings/wpm_target_max/", {"value": 20}, format="json")
        recording_id = self.upload().data["id"]
        data = self.api.get("/api/v1/recordings/%s/analysis/" % recording_id).data
        self.assertEqual(data["pacing"]["status"], "too_fast")
        self.assertEqual(data["pacing"]["target_max"], 20)
