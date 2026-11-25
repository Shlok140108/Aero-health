from dataclasses import dataclass
from .models import MessageTemplate
from .personas import advice_for, category_name, persona_for_profile

COPY = {
"en": {"current_aqi": ("Air quality alert", "{place}: AQI is {aqi} ({category}){source_note}. {advice}"), "forecast_aqi": ("Air quality forecast", "AQI near {place} may reach {aqi} ({category}) in about {hours} hours. {advice}"), "smoke_arrival": ("Nearby smoke activity", "Predicted fire-related smoke activity is within {radius} km of {place}. Monitor local air quality and limit outdoor exposure if conditions worsen."), "stagnation": ("Pollution may linger", "AQI near {place} is {aqi}; low ventilation may allow pollution to linger. {advice}"), "all_clear": ("Air quality has improved", "AQI near {place} is now below your alert threshold. Keep checking local conditions.")},
"hi": {"current_aqi": ("वायु गुणवत्ता चेतावनी", "{place}: AQI {aqi} ({category}){source_note}. {advice}"), "forecast_aqi": ("वायु गुणवत्ता पूर्वानुमान", "{place} के पास लगभग {hours} घंटे में AQI {aqi} ({category}) हो सकता है। {advice}"), "smoke_arrival": ("धुएँ की गतिविधि", "{place} से {radius} किमी के भीतर आग से जुड़े धुएँ की गतिविधि का अनुमान है। स्थानीय वायु गुणवत्ता पर नज़र रखें।"), "stagnation": ("प्रदूषण ठहर सकता है", "{place} के पास AQI {aqi} है; कम वेंटिलेशन से प्रदूषण बना रह सकता है। {advice}"), "all_clear": ("वायु गुणवत्ता में सुधार", "{place} का AQI आपके अलर्ट स्तर से नीचे है। स्थानीय स्थिति देखते रहें।")},
"mr": {"current_aqi": ("हवेच्या गुणवत्तेचा इशारा", "{place}: AQI {aqi} ({category}){source_note}. {advice}"), "forecast_aqi": ("हवेच्या गुणवत्तेचा अंदाज", "{place} येथे सुमारे {hours} तासांत AQI {aqi} ({category}) होऊ शकतो. {advice}"), "smoke_arrival": ("धुराच्या हालचालीचा इशारा", "{place} पासून {radius} किमीमध्ये आगीशी संबंधित धुराची शक्यता आहे. स्थानिक हवेच्या गुणवत्तेवर लक्ष ठेवा."), "stagnation": ("प्रदूषण टिकून राहू शकते", "{place}: AQI {aqi}; कमी वायुवीजनामुळे प्रदूषण टिकू शकते. {advice}"), "all_clear": ("हवेच्या गुणवत्तेत सुधारणा", "{place} येथील AQI तुमच्या सूचना मर्यादेपेक्षा कमी झाला आहे.")},
"ta": {"current_aqi": ("காற்றுத் தர எச்சரிக்கை", "{place}: AQI {aqi} ({category}){source_note}. {advice}"), "forecast_aqi": ("காற்றுத் தர முன்னறிவிப்பு", "{place} அருகே சுமார் {hours} மணிநேரத்தில் AQI {aqi} ({category}) ஆகலாம். {advice}"), "smoke_arrival": ("புகை செயல்பாட்டு எச்சரிக்கை", "{place} பகுதியில் {radius} கிமீக்குள் தீ தொடர்பான புகை இருக்கலாம். உள்ளூர் காற்றுத் தரத்தைக் கவனிக்கவும்."), "stagnation": ("மாசு நீடிக்கலாம்", "{place}: AQI {aqi}; குறைந்த காற்றோட்டத்தால் மாசு நீடிக்கலாம். {advice}"), "all_clear": ("காற்றுத் தரம் மேம்பட்டது", "{place} பகுதியில் AQI உங்கள் எச்சரிக்கை வரம்புக்குக் கீழே உள்ளது.")},
"bn": {"current_aqi": ("বায়ুর মান সতর্কতা", "{place}: AQI {aqi} ({category}){source_note}. {advice}"), "forecast_aqi": ("বায়ুর মান পূর্বাভাস", "{place}-এর কাছে প্রায় {hours} ঘণ্টায় AQI {aqi} ({category}) হতে পারে। {advice}"), "smoke_arrival": ("ধোঁয়ার কার্যকলাপ সতর্কতা", "{place} এলাকার {radius} কিমির মধ্যে আগুন-সম্পর্কিত ধোঁয়া থাকতে পারে। স্থানীয় বায়ুর মান লক্ষ্য করুন।"), "stagnation": ("দূষণ জমে থাকতে পারে", "{place}: AQI {aqi}; কম বায়ু চলাচলে দূষণ থাকতে পারে। {advice}"), "all_clear": ("বায়ুর মানের উন্নতি", "{place}-এ AQI আপনার সতর্কতার সীমার নিচে নেমেছে।")}}

@dataclass
class Rendered:
    title: str
    body: str

def render(profile, decision, channel):
    lang=profile.alert_language if profile.alert_language in COPY else "en"
    template=MessageTemplate.objects.filter(alert_type=decision.alert_type,language=lang,channel=channel,is_active=True).first()
    title,body=(template.title,template.body) if template else COPY[lang].get(decision.alert_type,COPY["en"][decision.alert_type])
    source_note = " (ground-station reading)" if decision.source == "ground_sensor" else (" (forecast estimate)" if decision.source == "forecast" else " (satellite/model estimate)")
    values={"place":decision.place or "your saved location","aqi":round(decision.aqi) if decision.aqi is not None else "","category":category_name(decision.severity,lang),"hours":decision.hours or "","radius":decision.radius_km or "","source_note":source_note,"advice":advice_for(persona_for_profile(profile),lang,decision.severity)}
    body=body.format_map(values)
    if channel=="sms" and len(body)>300: body=body[:299].rstrip()+"…"
    return Rendered(title.format_map(values),body)
