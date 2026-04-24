"""
Alert message composer — generates SMS, WhatsApp, and voice-ready messages.
Multilingual support for all 7 languages.
"""

from utils.crop_profiles import get_crop_profile
from utils.logger import get_logger

logger = get_logger("alert_composer")

# Alert templates in Hindi (primary) — others via translation layer
ALERT_TEMPLATES = {
    "frost": {
        "sms": "⚠️ FROST ALERT: {crop_hi} mein pala girne ka khatra ({temp}°C). Aaj raat sinchai karein ya dhaka lagaein. -KisanMitra",
        "whatsapp": "🥶 *पाला चेतावनी* — आपकी {crop_hi} फसल के लिए\n\n🌡️ तापमान गिरकर *{temp}°C* होगा\n\n✅ अभी करें:\n• रात को हल्की सिंचाई करें\n• फसल को धका लगाएं\n• निचले इलाकों पर ध्यान दें\n\n_KisanMitra द्वारा सूचना_",
        "voice": "Kisan bhai, aapki {crop_hi} fasal mein aaj raat pala girne ka khatra hai. Taapmaan {temp} degree tak gir sakta hai. Kripya aaj raat sinchai karein aur fasal ko dhakein.",
    },
    "heatwave": {
        "sms": "🌡️ HEAT ALERT: Aaj {temp}°C tak garm hoga. {crop_hi} ko subah 5-7 baje sinchai karein. -KisanMitra",
        "whatsapp": "☀️ *लू चेतावनी* — आपकी {crop_hi} फसल के लिए\n\n🌡️ आज तापमान *{temp}°C* तक पहुंचेगा\n\n✅ अभी करें:\n• सुबह 5-7 बजे सिंचाई करें\n• दोपहर में सिंचाई न करें\n• छाया की व्यवस्था करें\n\n_KisanMitra द्वारा सूचना_",
        "voice": "Kisan bhai, aaj bahut garmi padegi. Taapmaan {temp} degree tak pahunchega. {crop_hi} ko subah 5 se 7 baje ke beech sinchai karein. Dopahar mein paani bilkul na dein.",
    },
    "excess_rain": {
        "sms": "🌧️ RAIN ALERT: Aaj {rain}mm baarish ki sambhavna. {crop_hi} ke khet ki naali saaf karein. Sinchai band karein. -KisanMitra",
        "whatsapp": "🌧️ *अत्यधिक वर्षा चेतावनी* — आपकी {crop_hi} फसल के लिए\n\n💧 आज *{rain}mm* बारिश की संभावना\n\n✅ अभी करें:\n• खेत की नाली साफ करें\n• आज सिंचाई बंद रखें\n• जलभराव से बचाएं\n\n_KisanMitra द्वारा सूचना_",
        "voice": "Kisan bhai, aaj {rain} milimeter baarish hone ki sambhavna hai. {crop_hi} ke khet ki naaliyan abhi saaf karein aur aaj sinchai band karein.",
    },
    "high_wind": {
        "sms": "💨 WIND ALERT: Aaj {wind}km/h tez hawa. {crop_hi} par keetnashak na sprinkle karein. -KisanMitra",
        "whatsapp": "💨 *तेज हवा चेतावनी* — आपकी {crop_hi} फसल के लिए\n\n🌬️ आज हवा की गति *{wind} km/h* रहेगी\n\n✅ अभी करें:\n• आज कीटनाशक का छिड़काव न करें\n• लंबी फसल को सहारा दें\n• फसल की जांच करें\n\n_KisanMitra द्वारा सूचना_",
        "voice": "Kisan bhai, aaj {wind} kilometer per ghante ki tez hawa chalegi. Kripya aaj keetnashak ka chhidkav na karein. Lambi fasal ko sahara dein.",
    },
    "flash_flood": {
        "sms": "🚨 FLOOD ALERT: Aapke khet mein barh ka khatra! Oonche sthan par jayen. District authority ko soochit karein. -KisanMitra",
        "whatsapp": "🚨 *बाढ़ की EMERGENCY चेतावनी*\n\n⚠️ आपके खेत में बाढ़ का अत्यंत खतरा है!\n\n❗ तुरंत करें:\n• ऊंचे स्थान पर जाएं\n• मवेशियों को सुरक्षित स्थान पर ले जाएं\n• जिला प्रशासन को सूचित करें: 112\n\n_KisanMitra EMERGENCY सूचना_",
        "voice": "EMERGENCY — Kisan bhai, aapke khet mein barh ka bahut bada khatra hai. Kripya abhi oonche sthan par jayen aur apne pashuo ko surakshit jagah le jayen. Jila prashasan ko 112 par call karein.",
    }
}

SEVERITY_EMOJI = {1: "ℹ️", 2: "⚠️", 3: "🔴", 4: "🚨", 5: "🆘"}


def compose_alert(risk: dict, crop: str, channel: str = "whatsapp") -> str:
    """
    Compose alert message for a detected risk.
    
    Args:
        risk: Risk dict from risk_classifier
        crop: Crop name string
        channel: 'sms' | 'whatsapp' | 'voice'
    """
    risk_type = risk.get("type", "none")
    if risk_type == "none" or risk_type not in ALERT_TEMPLATES:
        return ""

    try:
        profile = get_crop_profile(crop)
        crop_hi = profile["name_hi"]
    except Exception:
        crop_hi = crop

    template = ALERT_TEMPLATES[risk_type].get(channel, "")
    if not template:
        return ""

    # Extract values from risk
    detected = risk.get("detected_value", "")
    temp = detected.replace("°C", "").strip() if "°C" in detected else "—"
    rain = detected.replace("mm", "").strip() if "mm" in detected else "—"
    wind = detected.replace("km/h", "").strip() if "km/h" in detected else "—"

    message = template.format(
        crop_hi=crop_hi,
        temp=temp,
        rain=rain,
        wind=wind
    )

    severity = risk.get("severity", 1)
    emoji = SEVERITY_EMOJI.get(severity, "⚠️")

    if channel == "sms":
        # SMS: keep under 160 chars
        return message[:160]

    return message


def compose_daily_briefing(crop: str, daily_risks: list, irrigation_day: dict, language: str = "hi") -> str:
    """
    Compose morning daily briefing message (sent at 6 AM).
    """
    try:
        profile = get_crop_profile(crop)
        crop_hi = profile["name_hi"]
    except Exception:
        crop_hi = crop

    today_risks = daily_risks[0] if daily_risks else {}
    risk_count = today_risks.get("total_risks_detected", 0)
    max_sev = today_risks.get("max_severity", 0)
    irrigation = irrigation_day.get("decision", "IRRIGATE")
    irrigation_emoji = {"IRRIGATE": "💧", "SKIP": "⏭️", "REDUCE": "🔽"}.get(irrigation, "💧")

    briefing = f"""🌅 *सुप्रभात — KisanMitra सुबह की रिपोर्ट*

🌾 फसल: {crop_hi}
📅 आज का सारांश:

{irrigation_emoji} *सिंचाई:* {irrigation}
   {irrigation_day.get('reason', '')}

"""
    if risk_count > 0:
        briefing += f"⚠️ *आज {risk_count} मौसम जोखिम detected*\n"
        for r in today_risks.get("risks", []):
            briefing += f"   • {r['type'].upper()}: {r['severity_label']} — {r['advisory'][:80]}...\n"
    else:
        briefing += "✅ *आज कोई मौसम जोखिम नहीं* — फसल सुरक्षित है\n"

    briefing += "\n_KisanMitra — हर किसान का मौसम साथी_ 🌾"
    return briefing
