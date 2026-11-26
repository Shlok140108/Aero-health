"""Dashboard + live weather tests. Upstream HTTP (Open-Meteo, Nominatim) is mocked with
fixtures shaped like the real responses, so the suite runs offline."""
from unittest import mock

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from weather.ml_service import predict_aqi, predict_aqi_batch

DAYS = [f"2026-11-{10 + d}" for d in range(7)]


def hours(n_days):
    return [f"{DAYS[d]}T{h:02d}:00" for d in range(n_days) for h in range(24)]


def forecast_fixture(code=2):
    weatherapi_codes = {0: 1000, 1: 1003, 2: 1003, 3: 1009, 45: 1135, 48: 1147,
                        51: 1150, 53: 1153, 55: 1171, 56: 1168, 57: 1171, 61: 1183,
                        63: 1189, 65: 1195, 66: 1198, 67: 1201, 80: 1240, 81: 1243,
                        82: 1246, 95: 1276}
    weatherapi_code = weatherapi_codes.get(code, 1003)
    condition = {"code": weatherapi_code, "text": "Partly cloudy", "icon": "//example.test/icon.png"}
    t = hours(7)
    hourly = []
    for i, time in enumerate(t):
        hourly.append({
            "time": time.replace("T", " "),
            "temp_c": 25 + (i % 24) / 3,
            "chance_of_rain": 70 if i % 24 == 18 else 5,
            "condition": condition,
            "is_day": 1 if 6 <= i % 24 <= 18 else 0,
            "vis_km": 10,
            "dewpoint_c": 18.2,
            "uv": 6.4,
        })
    forecastday = []
    for i, date in enumerate(DAYS):
        forecastday.append({
            "date": date,
            "day": {
                "maxtemp_c": 32 + i, "mintemp_c": 20,
                "daily_chance_of_rain": [10, 20, 30, 40, 50, 60, 70][i],
                "totalprecip_mm": [0.0, None, 1.2, 0, 0, 0, 3.4][i],
                "uv": 7.1, "condition": condition,
            },
            "astro": {"sunrise": "06:40 AM", "sunset": "06:05 PM"},
            "hour": hourly[i * 24:(i + 1) * 24],
        })
    return {
        "location": {"tz_id": "Asia/Kolkata"},
        "current": {
            "last_updated": "2026-11-10 14:15", "temp_c": 31.4, "feelslike_c": 33.0, "humidity": 52,
            "is_day": 1, "precip_mm": 0.0, "condition": condition, "cloud": 40, "pressure_mb": 1009.6,
            "wind_kph": 11.2, "wind_degree": 250, "gust_kph": 22.0,
        },
        "forecast": {"forecastday": forecastday},
    }


def air_fixture(days=2):
    t = hours(days)
    n = len(t)
    return {"hourly": {"time": t, "pm10": [120.0] * n, "pm2_5": [60.0 + i % 24 for i in range(n)],
                       "carbon_monoxide": [400.0] * n, "nitrogen_dioxide": [30.0] * n,
                       "sulphur_dioxide": [8.0] * n, "ozone": [45.0] * n},
            "current": {"time": "2026-11-10T14:15", "us_aqi": 151, "pm10": 120.0, "pm2_5": 70.0,
                        "carbon_monoxide": 400.0, "nitrogen_dioxide": 30.0, "sulphur_dioxide": 8.0, "ozone": 45.0}}


class Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status

    def json(self): return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def fake_get(url, params=None, **kw):
    if "air-quality-api" in url:
        return Resp(air_fixture(params.get("forecast_days", 2) if params and "hourly" in params else 2))
    if "api.weatherapi.com" in url:
        payload = forecast_fixture()
        payload["forecast"]["forecastday"] = payload["forecast"]["forecastday"][:int(params.get("days", 3))]
        return Resp(payload)
    if "geocoding-api" in url:
        return Resp({"results": [{"name": "Pune", "admin1": "Maharashtra", "country": "India",
                                  "latitude": 18.51957, "longitude": 73.85535}]})
    if "nominatim" in url:
        return Resp({"address": {"suburb": "Hinjewadi", "city": "Pune", "state": "Maharashtra"}})
    return Resp(forecast_fixture())


class Base(TestCase):
    def setUp(self):
        cache.clear()
        key_patch = mock.patch("django.conf.settings.WEATHER_API_KEY", "test-weather-key")
        key_patch.start()
        self.addCleanup(key_patch.stop)
        p = mock.patch("requests.get", side_effect=fake_get)
        self.get = p.start()
        self.addCleanup(p.stop)


class ModelTests(SimpleTestCase):
    def test_batch_returns_clipped_floats(self):
        nan = float("nan")
        row = dict(zip(["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2", "O3", "Benzene", "Toluene",
                        "lat", "lon", "month", "Day_of_week"],
                       [60, 120, nan, 30, nan, nan, 0.4, 8, 45, nan, nan, 18.5, 73.8, 11, 1]))
        out = predict_aqi_batch([row, row])
        self.assertEqual(len(out), 2)
        self.assertTrue(all(isinstance(v, float) and 0 <= v <= 500 for v in out))
        self.assertEqual(predict_aqi_batch([]), [])

    def test_single_predict_derives_month_and_weekday_from_date(self):
        from datetime import datetime
        nan = float("nan")
        v = predict_aqi(60, 120, nan, 30, nan, nan, 0.4, 8, 45, nan, nan, 18.5, 73.8, date=datetime(2026, 11, 10))
        self.assertIsInstance(v, float)


class OverviewTests(Base):
    def test_overview_ok(self):
        r = self.client.get("/api/overview/", {"lat": 18.52, "lon": 73.85, "place": "Pune"})
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(d["place"], "Pune")
        self.assertEqual(len(d["hourly"]), 8)
        self.assertEqual(len(d["curve"]), 12)
        self.assertEqual(len(d["week"]), 3)
        weather_call = next(call for call in self.get.call_args_list if "api.weatherapi.com" in call.args[0])
        self.assertEqual(weather_call.kwargs["params"]["days"], 3)
        self.assertEqual(weather_call.kwargs["params"]["key"], "test-weather-key")
        self.assertTrue(0 <= d["aqi"]["value"] <= 500)
        self.assertRegex(d["rain"], r"^\d+\.\d mm today$")

    def test_null_precip_sum_does_not_crash(self):
        # fixture has None in precipitation_sum[1]; today's value is fine, but make today's None too
        f = forecast_fixture(); f["forecast"]["forecastday"][0]["day"]["totalprecip_mm"] = None
        with mock.patch("requests.get", side_effect=lambda u, params=None, **k:
                        Resp({**f, "forecast": {"forecastday": f["forecast"]["forecastday"][:3]}})
                        if "api.weatherapi.com" in u else fake_get(u, params)):
            r = self.client.get("/api/overview/", {"lat": 18.52, "lon": 73.85})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["rain"], "0.0 mm today")

    def test_bad_coords_400(self):
        for q in ({"lat": "abc", "lon": "1"}, {"lat": "nan", "lon": "77"}, {"lat": 95, "lon": 77},
                  {"lat": 51.5, "lon": -0.12}):          # last one: valid but outside India for the AQI model
            self.assertEqual(self.client.get("/api/overview/", q).status_code, 400, q)

    def test_upstream_failure_is_502(self):
        self.get.side_effect = requests.ConnectionError("down")
        self.assertEqual(self.client.get("/api/overview/", {"lat": 18.5, "lon": 73.8}).status_code, 502)

    def test_overview_serves_last_successful_response_when_upstream_is_limited(self):
        params = {"lat": 18.5, "lon": 73.8}
        self.assertEqual(self.client.get("/api/overview/", params).status_code, 200)
        cache.delete("overview:weatherapi:18.5:73.8")
        self.get.side_effect = requests.HTTPError("429 Too Many Requests")

        response = self.client.get("/api/overview/", params)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["stale"])


class PredictionTests(Base):
    def test_prediction_ok(self):
        r = self.client.get("/api/prediction/", {"lat": 18.52, "lon": 73.85})
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(len(d["days"]), 3)
        self.assertIsNotNone(d["days"][0]["aqi_max"])
        self.assertIn("band", d["advice"])
        self.assertIsNotNone(d["typical_temp_today"])

    def test_outside_india_400(self):
        self.assertEqual(self.client.get("/api/prediction/", {"lat": 40.7, "lon": -74}).status_code, 400)


class LiveTests(Base):
    def test_live_shape(self):
        r = self.client.get("/api/live/", {"lat": 18.5204, "lon": 73.8567})
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        c = d["current"]
        self.assertEqual((c["temp"], c["feels"], c["humidity"]), (31, 33, 52))
        self.assertEqual(c["wind_dir"], "WSW")
        self.assertEqual(c["desc"], "Partly cloudy")
        self.assertEqual(c["visibility_km"], 10.0)
        self.assertEqual(len(d["hourly"]), 24)
        self.assertEqual(d["hourly"][0]["label"], "Now")
        self.assertEqual(d["hourly"][1]["label"], "3 PM")         # current time is 14:15
        self.assertEqual(len(d["daily"]), 3)
        self.assertEqual(d["daily"][0]["day"], "Today")
        self.assertEqual(d["sun"], {"rise": "6:40 AM", "set": "6:05 PM"})
        self.assertEqual(d["aqi"]["us_aqi"], 151)
        self.assertTrue(0 <= d["aqi"]["cpcb"] <= 500)               # Indian location -> model estimate

    def test_outside_india_has_no_cpcb_estimate_but_works(self):
        r = self.client.get("/api/live/", {"lat": 51.5, "lon": -0.12})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["aqi"]["cpcb"])

    def test_air_api_down_still_returns_weather(self):
        def flaky(url, params=None, **k):
            if "air-quality" in url: raise requests.ConnectionError("down")
            return fake_get(url, params)
        self.get.side_effect = flaky
        r = self.client.get("/api/live/", {"lat": 18.5, "lon": 73.8})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["aqi"])

    def test_weather_down_is_502_with_message(self):
        self.get.side_effect = requests.ConnectionError("down")
        r = self.client.get("/api/live/", {"lat": 18.5, "lon": 73.8})
        self.assertEqual(r.status_code, 502)
        self.assertIn("unreachable", r.json()["error"])

    def test_live_weather_serves_last_successful_response_when_upstream_is_limited(self):
        params = {"lat": 18.5, "lon": 73.8}
        self.assertEqual(self.client.get("/api/live/", params).status_code, 200)
        cache.delete("live:weatherapi:18.5:73.8")
        self.get.side_effect = requests.HTTPError("429 Too Many Requests")

        response = self.client.get("/api/live/", params)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["stale"])

    def test_weather_update_fetch_is_cached_for_15_minutes(self):
        from .live import fetch_current_weather

        payload = {
            "current": {
                "time": "2026-11-26T10:00",
                "temperature_2m": 27,
                "apparent_temperature": 28,
                "relative_humidity_2m": 60,
                "precipitation": 0,
                "weather_code": 0,
                "wind_speed_10m": 8,
                "is_day": 1,
            },
            "hourly": {
                "time": ["2026-11-26T10:00"],
                "precipitation_probability": [5],
            },
        }
        with mock.patch("dashboard.live._get_weather_forecast", return_value=payload) as get_weather:
            first = fetch_current_weather(18.52, 73.85)
            second = fetch_current_weather(18.52, 73.85)

        self.assertEqual(first, second)
        get_weather.assert_called_once()

    def test_validation(self):
        for q in ({"lat": "x", "lon": "1"}, {"lat": "inf", "lon": "1"}, {"lat": 91, "lon": 0}, {"lat": 0, "lon": 181}):
            self.assertEqual(self.client.get("/api/live/", q).status_code, 400, q)

    def test_cached_for_nearby_repeat_requests(self):
        self.client.get("/api/live/", {"lat": 18.5204, "lon": 73.8567})
        calls = self.get.call_count
        self.client.get("/api/live/", {"lat": 18.5211, "lon": 73.8571})   # ~100 m away, same 2-dp cell
        self.assertEqual(self.get.call_count, calls)

    def test_night_icon_and_theme(self):
        f = forecast_fixture(code=0); f["current"]["is_day"] = 0
        self.get.side_effect = lambda u, params=None, **k: Resp(f) if "air-quality" not in u else fake_get(u, params)
        c = self.client.get("/api/live/", {"lat": 18.5, "lon": 73.8}).json()["current"]
        self.assertEqual((c["icon"], c["theme"]), ("🌙", "clear-night"))


class GeocodeReverseTests(Base):
    def test_geocode(self):
        r = self.client.get("/api/geocode/", {"q": "Pune"}).json()["results"]
        self.assertEqual(r[0]["label"], "Pune, Maharashtra, India")
        self.assertEqual(r[0]["lat"], 18.51957)

    def test_geocode_short_query_makes_no_upstream_call(self):
        self.assertEqual(self.client.get("/api/geocode/", {"q": "a"}).json(), {"results": []})
        self.get.assert_not_called()

    def test_reverse_label(self):
        d = self.client.get("/api/reverse/", {"lat": 18.5913, "lon": 73.7389}).json()
        self.assertEqual(d, {"label": "Hinjewadi, Pune", "resolved": True})

    def test_reverse_falls_back_to_coordinates(self):
        self.get.side_effect = requests.ConnectionError("blocked")
        d = self.client.get("/api/reverse/", {"lat": 18.5913, "lon": 73.7389}).json()
        self.assertEqual(d, {"label": "18.591, 73.739", "resolved": False})

    def test_reverse_requires_coords(self):
        self.assertEqual(self.client.get("/api/reverse/").status_code, 400)

    def test_reverse_sends_user_agent(self):
        self.client.get("/api/reverse/", {"lat": 18.5913, "lon": 73.7389})
        self.assertIn("AeroHealth", self.get.call_args.kwargs["headers"]["User-Agent"])


class PageTests(Base):
    def test_pages_render(self):
        for path in ("/", "/weather/", "/prediction/", "/account/", "/login/", "/signed-out/"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_header_language_and_theme_controls_and_dashboard_city_search(self):
        html = self.client.get("/").content.decode()
        for needle in ('id="langSelect"', 'id="themebtn"', 'id="gsearch"'):
            self.assertIn(needle, html)
        self.assertNotIn('id="city"', html)

    def test_weather_page_has_tracker_and_live_button(self):
        html = self.client.get("/weather/").content.decode()
        for needle in ("id=\"livebtn\"", "id=\"trk-btn\"", "weather.js", "location.js", "leaflet.js"):
            self.assertIn(needle, html)
