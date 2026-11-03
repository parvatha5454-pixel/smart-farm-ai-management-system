import unittest
from unittest import mock

import requests

from services import weather
from services.ai.validation import ToolError


def resp(json_data, status=200):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = json_data
    r.raise_for_status.side_effect = None if status < 400 else requests.HTTPError("bad")
    return r


GEO = {"results": [{"name": "Madurai", "admin1": "Tamil Nadu", "country": "India",
                    "latitude": 9.9, "longitude": 78.1}]}
FORECAST = {"daily": {
    "time": ["2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20"],
    "temperature_2m_max": [34.0, 35.5, 33.0, 30.0],
    "temperature_2m_min": [24.0, 25.0, 24.0, 23.0],
    "precipitation_sum": [0.0, 1.2, None, 8.0],
    "precipitation_probability_max": [5, 20, 10, 60]}}


class WeatherTests(unittest.TestCase):
    def setUp(self):
        weather.clear_cache()

    def test_successful_forecast(self):
        with mock.patch("services.weather.requests.get", side_effect=[resp(GEO), resp(FORECAST)]):
            r = weather.get_forecast("Madurai")
        self.assertTrue(r["available"])
        self.assertEqual(r["location"], "Madurai, Tamil Nadu, India")
        self.assertEqual(len(r["days"]), 4)
        self.assertEqual(r["summary"]["rain_next_3_days_mm"], 1.2)  # None ignored
        self.assertEqual(r["summary"]["max_temp_next_3_days_c"], 35.5)
        self.assertIn("Open-Meteo", r["source"])

    def test_result_is_cached(self):
        with mock.patch("services.weather.requests.get", side_effect=[resp(GEO), resp(FORECAST)]) as g:
            weather.get_forecast("Madurai")
            weather.get_forecast("madurai")
        self.assertEqual(g.call_count, 2)  # 2 calls for first lookup only

    def test_unknown_location(self):
        with mock.patch("services.weather.requests.get", return_value=resp({"results": []})):
            r = weather.get_forecast("Nowhereville")
        self.assertFalse(r["available"])
        self.assertIn("not found", r["reason"])

    def test_timeout_is_graceful(self):
        with mock.patch("services.weather.requests.get", side_effect=requests.Timeout()):
            r = weather.get_forecast("Madurai")
        self.assertFalse(r["available"])
        self.assertIn("timed out", r["reason"])

    def test_network_error_is_graceful(self):
        with mock.patch("services.weather.requests.get", side_effect=requests.ConnectionError()):
            r = weather.get_forecast("Madurai")
        self.assertFalse(r["available"])

    def test_http_error_is_graceful(self):
        with mock.patch("services.weather.requests.get", return_value=resp({}, status=500)):
            self.assertFalse(weather.get_forecast("Madurai")["available"])

    def test_malformed_payload_is_graceful(self):
        with mock.patch("services.weather.requests.get", side_effect=[resp(GEO), resp({"daily": {}})]):
            self.assertFalse(weather.get_forecast("Madurai")["available"])

    def test_invalid_location_raises_before_any_request(self):
        with mock.patch("services.weather.requests.get") as g:
            with self.assertRaises(ToolError):
                weather.get_forecast("bad;location")
        g.assert_not_called()

    def test_failed_lookups_are_not_cached(self):
        with mock.patch("services.weather.requests.get", side_effect=requests.Timeout()):
            weather.get_forecast("Madurai")
        with mock.patch("services.weather.requests.get", side_effect=[resp(GEO), resp(FORECAST)]):
            self.assertTrue(weather.get_forecast("Madurai")["available"])


if __name__ == "__main__":
    unittest.main()
