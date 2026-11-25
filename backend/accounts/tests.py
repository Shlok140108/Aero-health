from types import SimpleNamespace as NS
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from . import health_rules as hr
from .models import UserProfile

User = get_user_model()

SIGNUP = {
    "full_name": "Asha Rao", "username": "asha_r", "password1": "Tr1cky-Pass-93", "password2": "Tr1cky-Pass-93",
    "age": "29", "phone": "98765 43210", "email": "Asha@Example.com", "notify_email": "on",
    "occupation": "outdoor_labour", "job_title": "Mason", "outdoor_hours": "7", "gender": "F",
    "pregnancy_status": "pregnant", "trimester": "2", "conditions": ["asthma", "allergy"],
    "city": "Pune", "state": "Maharashtra", "lat": "18.5204", "lon": "73.8567",
}


class RuleTests(SimpleTestCase):
    def test_standard_adult_only_alerted_when_poor(self):
        p = NS(age=30, conditions=[], occupation="office", outdoor_hours=0, pregnancy_status="na")
        self.assertEqual(hr.sensitivity(p), "Standard")
        self.assertEqual(hr.aqi_threshold(p), 200)
        a = hr.personal_alerts(p, 90, 120, 30, 3, 0)
        self.assertEqual([x["title"] for x in a], ["All clear for you"])

    def test_asthma_pregnant_outdoor_worker_is_high(self):
        p = NS(age=29, conditions=["asthma"], occupation="outdoor_labour", outdoor_hours=7, pregnancy_status="pregnant")
        self.assertEqual(hr.sensitivity(p), "High")
        self.assertEqual(hr.aqi_threshold(p), 100)
        titles = [x["title"] for x in hr.personal_alerts(p, 130, 160, 37, 9, 0)]
        for t in ("Air quality is above your alert level", "Protect your lungs", "Extra care while pregnant", "Heat alert"):
            self.assertIn(t, titles)

    def test_severe_air_is_danger_and_sorted_first(self):
        p = NS(age=70, conditions=["heart"], occupation="retired", outdoor_hours=0, pregnancy_status="na")
        a = hr.personal_alerts(p, 320, 340, 30, 2, 0)
        self.assertEqual(a[0]["level"], "danger")
        self.assertLessEqual(len(a), 6)

    def test_guest_profile_none_works(self):
        self.assertEqual(hr.sensitivity(None), "Standard")
        self.assertTrue(hr.personal_alerts(None, 250, 250, 41, 0, 0))


class SignupTests(TestCase):
    def test_signup_creates_user_and_profile_and_logs_in(self):
        r = self.client.post("/signup/", SIGNUP)
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        u = User.objects.get(username="asha_r")
        self.assertTrue(u.check_password("Tr1cky-Pass-93"))
        self.assertNotIn("Tr1cky", u.password)                 # hashed
        self.assertEqual(u.email, "asha@example.com")
        p = u.profile
        self.assertEqual((p.age, p.phone, p.pregnancy_status, p.trimester), (29, "+919876543210", "pregnant", 2))
        self.assertEqual(sorted(p.conditions), ["allergy", "asthma"])
        self.assertEqual(self.client.get("/account/").status_code, 200)

    def test_pregnancy_ignored_for_men(self):
        r = self.client.post("/signup/", dict(SIGNUP, gender="M", pregnancy_status="pregnant"))
        self.assertEqual(r.status_code, 302)
        p = UserProfile.objects.get()
        self.assertEqual((p.pregnancy_status, p.trimester), ("na", None))

    def test_pregnant_requires_trimester(self):
        r = self.client.post("/signup/", dict(SIGNUP, trimester=""))
        self.assertEqual(r.status_code, 200)
        self.assertIn("trimester", r.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_none_of_these_means_empty_conditions(self):
        self.client.post("/signup/", dict(SIGNUP, conditions=["none"], gender="M"))
        self.assertEqual(UserProfile.objects.get().conditions, [])

    def test_validation_errors(self):
        for bad, field in [({"password2": "nope"}, "password2"), ({"password1": "12345678", "password2": "12345678"}, "password1"),
                           ({"phone": "12345"}, "phone"), ({"age": "9"}, "age"), ({"username": "a b"}, "username"),
                           ({"conditions": []}, "conditions"), ({"city": "", "lat": "", "lon": ""}, "city")]:
            r = self.client.post("/signup/", dict(SIGNUP, **bad))
            self.assertEqual(r.status_code, 200, bad)
            self.assertIn(field, r.context["form"].errors, bad)

    def test_duplicate_username_and_email(self):
        self.client.post("/signup/", SIGNUP); self.client.post("/logout/")
        r = self.client.post("/signup/", dict(SIGNUP, username="ASHA_R", email="other@example.com"))
        self.assertIn("username", r.context["form"].errors)
        r = self.client.post("/signup/", dict(SIGNUP, username="someone", email="ASHA@example.com"))
        self.assertIn("email", r.context["form"].errors)

    def test_signup_page_renders_all_five_steps(self):
        html = self.client.get("/signup/").content.decode()
        self.assertEqual(html.count('class="step"'), 5)


class LoginAccountTests(TestCase):
    def setUp(self):
        self.client.post("/signup/", SIGNUP); self.client.post("/logout/")

    def test_login_logout(self):
        self.assertEqual(self.client.post("/login/", {"username": "asha_r", "password": "bad"}).status_code, 200)
        r = self.client.post("/login/", {"username": "ASHA_R", "password": "Tr1cky-Pass-93"})
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/logout/").status_code, 405)          # POST only
        self.client.post("/logout/")
        self.assertRedirects(self.client.get("/account/"), "/login/?next=/account/")

    def test_open_redirect_blocked(self):
        r = self.client.post("/login/", {"username": "asha_r", "password": "Tr1cky-Pass-93", "next": "https://evil.example"})
        self.assertRedirects(r, "/", fetch_redirect_response=False)

    def test_account_edit_updates_profile_and_alerts(self):
        self.client.login(username="asha_r", password="Tr1cky-Pass-93")
        r = self.client.post("/account/", dict(SIGNUP, full_name="Asha R.", conditions=["none"], pregnancy_status="no", trimester=""))
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        u = User.objects.get(username="asha_r")
        self.assertEqual((u.first_name, u.profile.conditions, u.profile.pregnancy_status), ("Asha R.", [], "no"))

    def test_account_edit_keeps_own_email(self):
        self.client.login(username="asha_r", password="Tr1cky-Pass-93")
        r = self.client.post("/account/", SIGNUP)
        self.assertEqual(r.status_code, 302)


class OverviewIntegration(TestCase):
    SHARED = {"aqi": {"value": 130}, "curve": [120, 150, 170, 140], "hourly": [["Now", 30, 130, 10]] * 8,
              "weather": {"feels": 36, "hi": 38, "uv": "9 · Very high"}}

    def test_guest_and_member_get_different_alerts(self):
        g = hr.for_overview(NS(is_authenticated=False), self.SHARED)
        self.assertEqual(g["user"]["name"], "Guest"); self.assertIn("href", g["alerts"][-1])
        self.client.post("/signup/", SIGNUP)
        u = User.objects.get(username="asha_r")
        m = hr.for_overview(u, self.SHARED)
        self.assertEqual((m["user"]["name"], m["user"]["sensitivity"]), ("Asha Rao", "High"))
        self.assertIn("Extra care while pregnant", [a["title"] for a in m["alerts"]])

    def test_api_returns_alerts_without_polluting_cache(self):
        from backend.dashboard import api
        shared = dict(self.SHARED, place="x")
        with mock.patch.object(api, "build", return_value=shared):
            cache.clear()
            self.client.post("/signup/", SIGNUP)
            member = self.client.get("/api/overview/", {"lat": 18.5, "lon": 73.8}).json()
            self.client.post("/logout/")
            guest = self.client.get("/api/overview/", {"lat": 18.5, "lon": 73.8}).json()
        self.assertEqual(member["user"]["name"], "Asha Rao")
        self.assertEqual(guest["user"]["name"], "Guest")             # no leak through the shared cache


class GoogleFlowTests(TestCase):
    """The Google round trip itself needs real credentials; these cover everything around it."""

    def google_user(self):
        # what allauth creates after a successful Google callback: a user with no profile and no password
        u = User.objects.create(username="priya.s", email="priya@gmail.com", first_name="Priya Sharma")
        u.set_unusable_password(); u.save()
        self.client.force_login(u)
        return u

    def test_login_and_signup_pages_have_google_button(self):
        for url in ("/login/", "/signup/"):
            self.assertIn("Continue with Google", self.client.get(url).content.decode(), url)

    def test_google_button_posts_to_allauth_and_redirects_to_google(self):
        with self.settings(SOCIALACCOUNT_PROVIDERS={"google": {"APP": {"client_id": "x", "secret": "y", "key": ""},
                                                               "SCOPE": ["profile", "email"]}}):
            r = self.client.post("/accounts/google/login/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("accounts.google.com", r["Location"])

    def test_user_without_profile_is_sent_to_complete_profile(self):
        self.google_user()
        for url in ("/", "/weather/", "/account/"):
            self.assertRedirects(self.client.get(url), "/complete-profile/", fetch_redirect_response=False, msg_prefix=url)
        self.assertEqual(self.client.get("/api/cities/").status_code, 200)     # APIs stay reachable

    def test_complete_profile_saves_profile_and_unlocks_site(self):
        u = self.google_user()
        page = self.client.get("/complete-profile/").content.decode()
        self.assertEqual(page.count('class="step"'), 4)             # no account step
        self.assertIn("ALMOST THERE, PRIYA SHARMA", page)
        data = {k: v for k, v in SIGNUP.items() if k not in ("full_name", "username", "password1", "password2", "email")}
        r = self.client.post("/complete-profile/", dict(data, gender="M", pregnancy_status=""))
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.assertEqual(UserProfile.objects.get(user=u).phone, "+919876543210")
        self.assertEqual(self.client.get("/account/").status_code, 200)
        self.assertRedirects(self.client.get("/complete-profile/"), "/", fetch_redirect_response=False)

    def test_superuser_is_not_forced(self):
        User.objects.create_superuser("root", "r@x.com", "pw12345678")
        self.client.login(username="root", password="pw12345678")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_anonymous_cannot_open_complete_profile(self):
        self.assertRedirects(self.client.get("/complete-profile/"), "/login/?next=/complete-profile/")


class SignupMarkupTests(TestCase):
    def test_wizard_form_is_not_closed_early_by_a_nested_form(self):
        """A nested <form> makes browsers close the wizard form early; fields after it then drop out of it
        and the JS crashes. Everything up to the final submit button must be inside the one form."""
        html = self.client.get("/signup/").content.decode()
        start = html.index('id="profile-form"')
        inside = html[start:html.index("</form>", start)]
        self.assertNotIn("<form", inside)
        for field in ('name="age"', 'name="city"', 'name="conditions"', 'id="finish"'):
            self.assertIn(field, inside)
