"""Product defaults only; these are informational, not clinically validated thresholds."""
from accounts.models import OUTDOOR_OCCUPATIONS

LANGUAGES = ("en", "hi", "mr", "ta", "bn")
CATEGORY_NAMES = {
    "en": ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"],
    "hi": ["अच्छा", "संतोषजनक", "मध्यम", "खराब", "बहुत खराब", "गंभीर"],
    "mr": ["चांगला", "समाधानकारक", "मध्यम", "वाईट", "अतिशय वाईट", "गंभीर"],
    "ta": ["நல்லது", "திருப்திகரமானது", "மிதமானது", "மோசம்", "மிக மோசம்", "கடுமையானது"],
    "bn": ["ভালো", "সন্তোষজনক", "মাঝারি", "খারাপ", "খুব খারাপ", "গুরুতর"],
}
VERY_POOR = 4

def aqi_severity(aqi):
    for i, limit in enumerate((50, 100, 200, 300, 400)):
        if aqi <= limit: return i
    return 5

def category_name(severity, language="en"):
    return CATEGORY_NAMES.get(language, CATEGORY_NAMES["en"])[max(0, min(int(severity), 5))]

def persona_for_profile(profile):
    conditions = set(profile.conditions or [])
    if conditions.intersection({"asthma", "copd"}): return "asthma"
    if profile.age >= 65 or profile.occupation == "retired": return "elderly"
    if profile.occupation in OUTDOOR_OCCUPATIONS or (profile.outdoor_hours or 0) >= 4: return "outdoor_worker"
    if profile.age < 18: return "child"
    return "general"

def default_threshold(profile):
    return {"asthma": 101, "elderly": 101, "child": 101, "outdoor_worker": 201, "general": 201}[persona_for_profile(profile)]

def sensitivity_threshold(threshold, sensitivity):
    factor = {"standard": 1.0, "sensitive": 0.85, "high": 0.70}.get(sensitivity, 1.0)
    return max(1, int(round(threshold * factor)))

ADVICE = {
"en": {"general": ["Sensitive people should reduce prolonged outdoor exertion.", "Reduce outdoor activity and consider a well-fitting mask.", "Avoid outdoor exertion and follow local public-health advice."], "asthma": ["Keep your usual reliever medication available and limit hard outdoor exercise.", "Stay indoors where possible and follow your clinician's action plan.", "Stay indoors where possible; seek medical help if breathing worsens."], "elderly": ["Avoid long, strenuous outdoor activity.", "Keep outdoor time short and prefer cleaner hours.", "Stay indoors where possible and seek help if unwell."], "outdoor_worker": ["Take breaks in cleaner indoor air.", "Use suitable respiratory protection and take frequent breaks.", "Postpone outdoor work if possible; use suitable protection if it cannot be avoided."], "child": ["Keep strenuous outdoor play moderate.", "Prefer indoor play and shorter outdoor periods.", "Keep children indoors where possible."]},
"hi": {"general": ["संवेदनशील लोग लंबे समय तक बाहर मेहनत करने से बचें।", "बाहरी गतिविधि कम करें और उचित मास्क पर विचार करें।", "बाहर मेहनत करने से बचें और स्थानीय स्वास्थ्य सलाह मानें।"], "asthma": ["अपनी नियमित दवा पास रखें और बाहर कठिन व्यायाम सीमित करें।", "जहाँ संभव हो घर के अंदर रहें और डॉक्टर की योजना मानें।", "घर के अंदर रहें; साँस बिगड़ने पर चिकित्सा सहायता लें।"], "elderly": ["लंबी और कठिन बाहरी गतिविधि से बचें।", "बाहर कम समय बिताएँ और साफ हवा वाले समय को चुनें।", "जहाँ संभव हो घर में रहें और अस्वस्थ होने पर मदद लें।"], "outdoor_worker": ["साफ हवा वाली जगह पर नियमित विराम लें।", "उचित सुरक्षा पहनें और बार-बार विराम लें।", "संभव हो तो बाहरी काम टालें।"], "child": ["बच्चों का कठिन बाहरी खेल सीमित रखें।", "घर के अंदर खेलना बेहतर है।", "जहाँ संभव हो बच्चों को घर के अंदर रखें।"]},
"mr": {"general": ["संवेदनशील व्यक्तींनी बाहेर जास्त श्रम करणे टाळावे.", "बाहेरील हालचाल कमी करा आणि योग्य मास्क वापरण्याचा विचार करा.", "बाहेर श्रम करणे टाळा आणि स्थानिक आरोग्य सूचना पाळा."], "asthma": ["नेहमीची औषधे जवळ ठेवा आणि बाहेरील व्यायाम कमी करा.", "शक्यतो घरात राहा आणि डॉक्टरांचा सल्ला पाळा.", "शक्यतो घरात राहा; श्वास घेण्यास त्रास वाढल्यास वैद्यकीय मदत घ्या."], "elderly": ["दीर्घ आणि कष्टदायक बाहेरील हालचाल टाळा.", "बाहेर कमी वेळ घालवा.", "शक्यतो घरात राहा आणि अस्वस्थ वाटल्यास मदत घ्या."], "outdoor_worker": ["स्वच्छ हवेत नियमित विश्रांती घ्या.", "योग्य संरक्षण वापरा आणि वारंवार विश्रांती घ्या.", "शक्य असल्यास बाहेरील काम पुढे ढकला."], "child": ["मुलांचा कष्टदायक बाहेरील खेळ मर्यादित ठेवा.", "घरातील खेळांना प्राधान्य द्या.", "शक्यतो मुलांना घरात ठेवा."]},
"ta": {"general": ["உணர்திறன் உள்ளவர்கள் நீண்ட நேர வெளிப்புற உழைப்பைத் தவிர்க்கவும்.", "வெளிப்புறச் செயல்பாட்டைக் குறைத்து பொருத்தமான முகக்கவசத்தைப் பயன்படுத்தவும்.", "வெளிப்புற உழைப்பைத் தவிர்த்து உள்ளூர் சுகாதார ஆலோசனையைப் பின்பற்றவும்."], "asthma": ["வழக்கமான மருந்தை உடன் வைத்துக் கொண்டு கடினமான வெளிப்புற உடற்பயிற்சியைக் குறைக்கவும்.", "முடிந்தவரை வீட்டுக்குள் இருந்து மருத்துவர் திட்டத்தைப் பின்பற்றவும்.", "வீட்டுக்குள் இருக்கவும்; மூச்சுத்திணறல் அதிகரித்தால் மருத்துவ உதவி பெறவும்."], "elderly": ["நீண்ட கடினமான வெளிப்புறச் செயல்பாட்டைத் தவிர்க்கவும்.", "வெளியில் குறைந்த நேரம் செலவிடவும்.", "முடிந்தவரை வீட்டுக்குள் இருக்கவும்."], "outdoor_worker": ["சுத்தமான காற்றுள்ள இடத்தில் இடைவெளி எடுக்கவும்.", "பொருத்தமான பாதுகாப்பைப் பயன்படுத்தி அடிக்கடி ஓய்வு எடுக்கவும்.", "முடிந்தால் வெளிப்புறப் பணியை ஒத்திவைக்கவும்."], "child": ["குழந்தைகளின் கடினமான வெளிப்புற விளையாட்டைக் குறைக்கவும்.", "வீட்டுக்குள் விளையாடுவதைத் தேர்ந்தெடுக்கவும்.", "முடிந்தவரை குழந்தைகளை வீட்டுக்குள் வைத்திருக்கவும்."]},
"bn": {"general": ["সংবেদনশীল ব্যক্তিরা দীর্ঘক্ষণ বাইরে পরিশ্রম এড়িয়ে চলুন।", "বাইরের কাজ কমান এবং উপযুক্ত মাস্ক ব্যবহারের কথা ভাবুন।", "বাইরে পরিশ্রম এড়িয়ে স্থানীয় স্বাস্থ্য পরামর্শ মেনে চলুন।"], "asthma": ["নিয়মিত ওষুধ সঙ্গে রাখুন এবং কঠিন বাইরের ব্যায়াম কমান।", "সম্ভব হলে ঘরে থাকুন এবং চিকিৎসকের পরিকল্পনা মেনে চলুন।", "ঘরে থাকুন; শ্বাসকষ্ট বাড়লে চিকিৎসা সহায়তা নিন।"], "elderly": ["দীর্ঘ ও কষ্টকর বাইরের কাজ এড়িয়ে চলুন।", "বাইরে কম সময় কাটান।", "সম্ভব হলে ঘরে থাকুন।"], "outdoor_worker": ["পরিষ্কার বাতাসে নিয়মিত বিরতি নিন।", "উপযুক্ত সুরক্ষা ব্যবহার করে ঘন ঘন বিরতি নিন।", "সম্ভব হলে বাইরের কাজ স্থগিত রাখুন।"], "child": ["শিশুদের কঠিন বাইরের খেলাধুলা কমান।", "ঘরের ভিতরে খেলতে উৎসাহ দিন।", "সম্ভব হলে শিশুদের ঘরে রাখুন।"]}}

def advice_for(persona, language, severity):
    table = ADVICE.get(language, ADVICE["en"])
    tier = 0 if severity <= 2 else 1 if severity == 3 else 2
    return table.get(persona, table["general"])[tier]

PRESETS = {
"general": {"current_aqi": (True, 201, 6), "forecast_aqi": (False, 201, 6), "smoke_arrival": (True, 201, 12), "stagnation": (False, 201, 8)},
"asthma": {"current_aqi": (True, 101, 4), "forecast_aqi": (True, 101, 6), "smoke_arrival": (True, 101, 8), "stagnation": (True, 101, 8)},
"elderly": {"current_aqi": (True, 101, 4), "forecast_aqi": (True, 101, 6), "smoke_arrival": (True, 101, 8), "stagnation": (True, 101, 8)},
"outdoor_worker": {"current_aqi": (True, 201, 6), "forecast_aqi": (True, 201, 6), "smoke_arrival": (True, 201, 8), "stagnation": (False, 201, 8)},
"child": {"current_aqi": (True, 101, 4), "forecast_aqi": (True, 101, 6), "smoke_arrival": (True, 101, 8), "stagnation": (True, 101, 8)}}

def ensure_default_rules(profile):
    from .models import AlertRule
    persona = persona_for_profile(profile)
    for kind, (active, threshold, cooldown) in PRESETS[persona].items():
        AlertRule.objects.get_or_create(profile=profile, alert_type=kind, defaults={"is_active": active, "aqi_threshold": threshold, "cooldown_hours": cooldown, "horizon_hours": 72 if kind == "forecast_aqi" else 24, "allow_voice": persona == "elderly" and kind == "current_aqi"})
