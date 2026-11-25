"""Place at: backend/accounts/health_rules.py

Turns a user's stored profile + the current forecast into (a) a sensitivity level / alert
threshold and (b) a short list of personal alerts.

These are simple, transparent rules built on the CPCB AQI bands (50/100/200/300/400) and
general public-health guidance. They are informational, not medical advice: have a doctor
or public-health expert review the wording and thresholds before real-world use.
"""
from types import SimpleNamespace

OUTDOOR_OCCUPATIONS = {"outdoor_labour", "farmer", "driver"}
LEVEL_ORDER = {"danger": 0, "warn": 1, "info": 2}


def _g(p, name, default=None):
    return getattr(p, name, default) if p is not None else default


def _flags(p):
    """Boolean facts about the person that the rules and the risk score both use."""
    age = _g(p, "age")
    conds = set(_g(p, "conditions", []) or [])
    pregnant = _g(p, "pregnancy_status") == "pregnant"
    nursing = _g(p, "pregnancy_status") == "nursing"
    outdoor = (_g(p, "occupation") in OUTDOOR_OCCUPATIONS) or (_g(p, "outdoor_hours", 0) or 0) >= 4
    return SimpleNamespace(
        conds=conds, pregnant=pregnant, nursing=nursing, outdoor=outdoor,
        lung=bool(conds & {"asthma", "copd"}), heart="heart" in conds,
        child=age is not None and age <= 12, senior=age is not None and age >= 65,
        smoker=bool(_g(p, "smoker")), breathless=bool(_g(p, "breathless_in_smog")),
    )


def risk_points(p):
    """(points, tags). More points = more sensitive to polluted / hot air."""
    f, pts, tags = _flags(p), 0, []
    if f.lung:
        pts += 3; tags.append("Asthma-aware" if "asthma" in f.conds else "Lung-health aware")
    if f.heart:
        pts += 3; tags.append("Heart-aware")
    if f.pregnant:
        pts += 3; tags.append("Pregnancy-aware")
    elif f.nursing:
        pts += 1; tags.append("New-parent aware")
    if f.child:
        pts += 2; tags.append("Child")
    elif f.senior:
        pts += 2; tags.append("Senior")
    elif (_g(p, "age") or 0) >= 60:
        pts += 1
    if f.outdoor:
        pts += 2 if (_g(p, "outdoor_hours", 0) or 0) >= 4 else 1
        tags.append("Outdoor worker")
    for c in ("diabetes", "bp", "allergy", "kidney", "skin_eye"):
        if c in f.conds:
            pts += 1
    if f.smoker:
        pts += 1
    if f.breathless:
        pts += 1
    return pts, tags


def sensitivity(p):
    pts, _ = risk_points(p)
    return "High" if pts >= 5 else "Elevated" if pts >= 2 else "Standard"


def aqi_threshold(p):
    """AQI above which this person is alerted (CPCB scale)."""
    return {"High": 100, "Elevated": 150, "Standard": 200}[sensitivity(p)]


def persona(p):
    _, tags = risk_points(p)
    return " · ".join(tags[:2]) if tags else "Everyday explorer"


def _band(aqi):
    return 0 if aqi <= 100 else 1 if aqi <= 200 else 2 if aqi <= 300 else 3


def personal_alerts(p, aqi, aqi_peak, heat, uv, rain):
    """List of {level, title, text}, most urgent first. `heat` = feels-like / day-high in deg C."""
    f = _flags(p)
    out = []
    worst = max(aqi, aqi_peak)
    band = _band(worst)
    thr = aqi_threshold(p)

    def add(level, title, text):
        out.append({"level": level, "title": title, "text": text})

    if worst > thr:
        peak_txt = f" and may reach {aqi_peak} today" if aqi_peak > aqi else ""
        add("danger" if worst > 300 or worst > thr + 100 else "warn", "Air quality is above your alert level",
            f"AQI is {aqi} now{peak_txt}. Your alert level is {thr}.")

    if f.lung and band >= 1:
        add("danger" if band >= 2 else "warn", "Protect your lungs",
            "Keep your reliever inhaler with you and avoid exertion outdoors." if band == 1 else
            "Stay indoors where you can, follow your doctor's action plan, and seek care if breathing worsens.")
    elif f.lung and band == 0 and worst > 50:
        add("info", "Carry your inhaler", "Air is acceptable today, but keep your reliever inhaler close as usual.")

    if f.heart and band >= 1:
        add("danger" if band >= 2 else "warn", "Go easy on your heart",
            "Avoid heavy exertion outdoors today." if band == 1 else
            "Stay indoors and seek care if you notice chest discomfort or unusual tiredness.")

    if f.pregnant and (band >= 1 or worst > 100):
        add("warn" if band < 2 else "danger", "Extra care while pregnant",
            "Keep outdoor time short, avoid busy roads at peak hours, and consider an N95-type mask. "
            "Speak to your doctor if you feel unwell.")
    elif f.nursing and band >= 1:
        add("warn", "Fresh air for you and baby", "Keep outings short and prefer the cleaner hours of the day.")

    if (f.child or f.senior) and band >= 1:
        who = "children" if f.child else "older adults"
        add("warn" if band == 1 else "danger", "Shorter outings today",
            f"Air is hard on {who}: keep outdoor time short and prefer indoor activity." if band == 1 else
            "Stay indoors today and avoid outdoor exertion.")

    if f.outdoor and worst > 150:
        add("warn" if band < 2 else "danger", "Outdoor work: mask up",
            "Wear an N95-type mask, take regular breaks in cleaner air, and keep water handy.")

    if "allergy" in f.conds and worst > 100:
        add("info", "Dust and allergy tips",
            "Keep windows closed in peak hours and rinse your face and hands after being outdoors.")

    if "skin_eye" in f.conds and worst > 100:
        add("info", "Eye and skin comfort", "Avoid rubbing your eyes outdoors and rinse with clean water when you get home.")

    if (f.smoker or f.breathless) and band >= 1:
        add("info", "Your lungs feel it sooner",
            "Skip outdoor exercise today and choose a cleaner time for walks.")

    # heat
    sensitive_heat = f.pregnant or f.nursing or f.child or f.senior or f.heart or f.outdoor or bool(
        f.conds & {"diabetes", "bp", "kidney"})
    if heat >= 40 or (heat >= 36 and sensitive_heat):
        notes = []
        if f.outdoor:
            notes.append("take shade breaks every hour and avoid heavy work in the hottest hours")
        if f.pregnant:
            notes.append("rest in shade and speak to your doctor if you feel dizzy")
        if f.conds & {"diabetes", "bp", "kidney", "heart"}:
            notes.append("heat strains the body, so follow your doctor's advice on fluids and medicines")
        if f.child or f.senior:
            notes.append("check on children and older family members often")
        add("danger" if heat >= 40 else "warn", "Heat alert",
            "Very hot today: drink water regularly" + ("; " + "; ".join(notes) if notes else "") + ".")

    if uv >= 8 and (f.outdoor or f.child or f.pregnant or "skin_eye" in f.conds):
        add("info", "High UV", "Use sunscreen, a hat and sunglasses when outside.")

    if not out:
        add("info", "All clear for you", "Air and weather look comfortable for your profile right now.")

    out.sort(key=lambda a: LEVEL_ORDER[a["level"]])
    return out[:6]


def for_overview(user, data):
    """Per-user part of /api/overview/. `data` is the shared (cached) payload, which must stay
    user-independent; this adds {"user": ..., "alerts": [...]} on top of it."""
    profile = getattr(user, "profile", None) if getattr(user, "is_authenticated", False) else None
    try:
        uv = int(str(data["weather"]["uv"]).split()[0])
    except (KeyError, ValueError, IndexError):
        uv = 0
    aqi = data["aqi"]["value"]
    alerts = personal_alerts(
        profile, aqi, max([aqi] + list(data.get("curve", []))),
        max(data["weather"]["feels"], data["weather"]["hi"]), uv,
        max([h[3] for h in data.get("hourly", [])] or [0]))
    if profile is None:
        alerts.append({"level": "info", "title": "Make these alerts yours",
                       "text": "Create a free profile and alerts will match your age, work and health.",
                       "href": "/signup/"})
        return {"user": {"name": "Guest", "persona": "Sign in to personalise", "sensitivity": "Standard"},
                "alerts": alerts}
    return {"user": {"name": user.first_name or user.username, "persona": persona(profile),
                     "sensitivity": sensitivity(profile)},
            "alerts": alerts}
