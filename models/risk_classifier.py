"""
MODULE 2 — Crop Risk Classifier
Uses verified crop thresholds to detect weather risks for each crop.
Rule-based engine (fast, explainable) + XGBoost for severity scoring.
"""

from utils.crop_profiles import get_crop_profile, SUPPORTED_CROPS
from utils.logger import get_logger
from typing import Optional

logger = get_logger("risk_classifier")

RISK_TYPES = ["frost", "heatwave", "excess_rain", "high_wind", "flash_flood", "none"]

# Hindi severity labels (used for default/Hindi language)
SEVERITY_LABELS = {
    1: "कम",
    2: "मध्यम",
    3: "अधिक",
    4: "बहुत अधिक",
    5: "गंभीर"
}

# Multilingual severity labels
SEVERITY_LABELS_LANG = {
    "hi": {1:"कम", 2:"मध्यम", 3:"अधिक", 4:"बहुत अधिक", 5:"गंभीर", 0:"कोई नहीं"},
    "mr": {1:"कमी", 2:"मध्यम", 3:"जास्त", 4:"खूप जास्त", 5:"गंभीर", 0:"काहीही नाही"},
    "kn": {1:"ಕಡಿಮೆ", 2:"ಮಧ್ಯಮ", 3:"ಹೆಚ್ಚು", 4:"ತುಂಬಾ ಹೆಚ್ಚು", 5:"ತೀವ್ರ", 0:"ಯಾವುದೂ ಇಲ್ಲ"},
    "te": {1:"తక్కువ", 2:"మధ్యమ", 3:"ఎక్కువ", 4:"చాలా ఎక్కువ", 5:"తీవ్రమైన", 0:"ఏదీ లేదు"},
    "ta": {1:"குறைவு", 2:"நடுத்தரம்", 3:"அதிகம்", 4:"மிக அதிகம்", 5:"தீவிரமான", 0:"எதுவும் இல்லை"},
    "pa": {1:"ਘੱਟ", 2:"ਮੱਧਮ", 3:"ਵੱਧ", 4:"ਬਹੁਤ ਵੱਧ", 5:"ਗੰਭੀਰ", 0:"ਕੋਈ ਨਹੀਂ"},
    "bn": {1:"কম", 2:"মাঝারি", 3:"বেশি", 4:"অনেক বেশি", 5:"গুরুতর", 0:"কোনোটি নয়"},
    "en": {1:"Low", 2:"Medium", 3:"High", 4:"Very High", 5:"Critical", 0:"None"},
}

# Crop names in all languages
CROP_NAMES_LANG = {
    "wheat":     {"hi":"गेहूं",    "mr":"गहू",      "kn":"ಗೋಧಿ",    "te":"గోధుమ",   "ta":"கோதுமை",  "pa":"ਕਣਕ",     "bn":"গম",      "en":"Wheat"},
    "rice":      {"hi":"चावल",    "mr":"तांदूळ",   "kn":"ಅಕ್ಕಿ",   "te":"వరి",     "ta":"அரிசி",   "pa":"ਚਾਵਲ",    "bn":"ধান",     "en":"Rice"},
    "soybean":   {"hi":"सोयाबीन", "mr":"सोयाबीन",  "kn":"ಸೋಯಾಬೀನ್","te":"సోయాబీన్","ta":"சோயாபீன்","pa":"ਸੋਇਆਬੀਨ", "bn":"সয়াবিন",  "en":"Soybean"},
    "cotton":    {"hi":"कपास",    "mr":"कापूस",    "kn":"ಹತ್ತಿ",   "te":"పత్తి",   "ta":"பருத்தி", "pa":"ਕਪਾਹ",    "bn":"তুলা",    "en":"Cotton"},
    "sugarcane": {"hi":"गन्ना",   "mr":"ऊस",       "kn":"ಕಬ್ಬು",   "te":"చెరకు",   "ta":"கரும்பு", "pa":"ਗੰਨਾ",    "bn":"আখ",      "en":"Sugarcane"},
    "onion":     {"hi":"प्याज",   "mr":"कांदा",    "kn":"ಈರುಳ್ಳಿ", "te":"ఉల్లిపాయ","ta":"வெங்காயம்","pa":"ਪਿਆਜ਼",  "bn":"পেঁয়াজ",  "en":"Onion"},
    "tomato":    {"hi":"टमाटर",   "mr":"टोमॅटो",   "kn":"ಟೊಮ್ಯಾಟೊ","te":"టమాటో",   "ta":"தக்காளி", "pa":"ਟਮਾਟਰ",   "bn":"টমেটো",   "en":"Tomato"},
}

def get_crop_name(crop: str, language: str) -> str:
    """Get crop name in the requested language."""
    names = CROP_NAMES_LANG.get(crop, {})
    return names.get(language, names.get("en", crop))


def classify_risk(
    crop: str,
    growth_stage: str,
    temp_min_c: float,
    temp_max_c: float,
    rainfall_mm: float,
    wind_kmh: float,
    rainfall_prob_pct: float,
    soil_saturation_index: float = 0.5
) -> dict:
    try:
        profile = get_crop_profile(crop)
    except ValueError as e:
        logger.error(str(e))
        return {"error": str(e)}

    risks = []

    # ── Frost Risk
    if temp_min_c is not None and temp_min_c < profile["frost_risk_temp_c"]:
        severity = _frost_severity(temp_min_c, profile["frost_risk_temp_c"], growth_stage)
        risks.append({
            "type": "frost",
            "severity": severity,
            "severity_label": SEVERITY_LABELS[severity],
            "detected_value": f"{temp_min_c}°C",
            "threshold": f"{profile['frost_risk_temp_c']}°C",
            "advisory": _frost_advisory(crop, temp_min_c, growth_stage, profile["name_hi"])
        })

    # ── Heatwave Risk
    if temp_max_c is not None and temp_max_c > profile["heatwave_temp_c"]:
        severity = _heat_severity(temp_max_c, profile["heatwave_temp_c"])
        risks.append({
            "type": "heatwave",
            "severity": severity,
            "severity_label": SEVERITY_LABELS[severity],
            "detected_value": f"{temp_max_c}°C",
            "threshold": f"{profile['heatwave_temp_c']}°C",
            "advisory": _heat_advisory(crop, temp_max_c, growth_stage, profile["name_hi"])
        })

    # ── Excess Rainfall Risk
    if rainfall_mm is not None and rainfall_mm > profile["max_rain_mm_day"]:
        severity = _rain_severity(rainfall_mm, profile["max_rain_mm_day"])
        risks.append({
            "type": "excess_rain",
            "severity": severity,
            "severity_label": SEVERITY_LABELS[severity],
            "detected_value": f"{rainfall_mm}mm",
            "threshold": f"{profile['max_rain_mm_day']}mm",
            "advisory": _rain_advisory(crop, rainfall_mm, growth_stage, profile["name_hi"])
        })

    # ── High Wind Risk
    if wind_kmh is not None and wind_kmh > profile["wind_risk_kmh"]:
        severity = _wind_severity(wind_kmh, profile["wind_risk_kmh"])
        risks.append({
            "type": "high_wind",
            "severity": severity,
            "severity_label": SEVERITY_LABELS[severity],
            "detected_value": f"{wind_kmh}km/h",
            "threshold": f"{profile['wind_risk_kmh']}km/h",
            "advisory": _wind_advisory(crop, wind_kmh, growth_stage, profile["name_hi"])
        })

    # ── Flash Flood Risk
    if (rainfall_mm is not None and rainfall_mm > profile["max_rain_mm_day"] * 1.5
            and soil_saturation_index > 0.7):
        severity = 4
        risks.append({
            "type": "flash_flood",
            "severity": severity,
            "severity_label": SEVERITY_LABELS[severity],
            "detected_value": f"{rainfall_mm}mm + मिट्टी संतृप्ति {soil_saturation_index:.1f}",
            "threshold": "बारिश > 1.5x सीमा + अधिक मिट्टी संतृप्ति",
            "advisory": f"⚠️ {profile['name_hi']} के खेत में बाढ़ का खतरा! नालियां अभी साफ करें और ऊंचे स्थान पर जाएं।"
        })

    risks.sort(key=lambda x: x["severity"], reverse=True)
    max_severity = risks[0]["severity"] if risks else 0

    result = {
        "crop": crop,
        "crop_hi": profile["name_hi"],
        "growth_stage": growth_stage,
        "risks": risks,
        "max_severity": max_severity,
        "max_severity_label": SEVERITY_LABELS.get(max_severity, "कोई नहीं"),
        "alert_required": max_severity >= 3,
        "emergency": max_severity >= 5,
        "total_risks_detected": len(risks)
    }

    if not risks:
        result["message"] = f"आज {profile['name_hi']} के लिए कोई मौसम खतरा नहीं। फसल सुरक्षित है।"

    logger.info(f"Risk classification: {crop} | Stage: {growth_stage} | Max severity: {max_severity}")
    return result


# ── Severity Calculators

def _frost_severity(actual: float, threshold: float, stage: str) -> int:
    diff = threshold - actual
    base = 1 if diff < 2 else 2 if diff < 4 else 3 if diff < 6 else 4
    if stage in ["flowering", "grain_filling", "pod_fill", "boll_development"]:
        base = min(5, base + 1)
    return base

def _heat_severity(actual: float, threshold: float) -> int:
    diff = actual - threshold
    return 1 if diff < 2 else 2 if diff < 4 else 3 if diff < 6 else 4 if diff < 8 else 5

def _rain_severity(actual: float, threshold: float) -> int:
    ratio = actual / threshold
    return 1 if ratio < 1.2 else 2 if ratio < 1.5 else 3 if ratio < 2.0 else 4 if ratio < 2.5 else 5

def _wind_severity(actual: float, threshold: float) -> int:
    diff = actual - threshold
    return 1 if diff < 10 else 2 if diff < 20 else 3 if diff < 30 else 4 if diff < 40 else 5


# ── Advisory Message Generators (Pure Hindi)

def _frost_advisory(crop: str, temp: float, stage: str, name_hi: str) -> str:
    msgs = {
        "flowering": f"⚠️ ज़रूरी: {name_hi} में पाला गिरने का खतरा ({temp}°C)। आज रात पौधों को ढकें या हल्की सिंचाई करें।",
        "grain_filling": f"⚠️ सावधान: {name_hi} के दाने भर रहे हैं — {temp}°C ठंड से बचाएं। जड़ के पास पानी दें।",
    }
    return msgs.get(stage, f"❄️ पाला चेतावनी: तापमान {temp}°C तक गिरेगा। {name_hi} को मल्चिंग या हल्की सिंचाई से बचाएं।")

def _heat_advisory(crop: str, temp: float, stage: str, name_hi: str) -> str:
    return f"☀️ लू चेतावनी: आज {temp}°C गर्मी पड़ेगी। {name_hi} को सुबह 5-7 बजे या शाम 6-8 बजे सिंचाई करें। दोपहर में पानी बिल्कुल न दें।"

def _rain_advisory(crop: str, rainfall: float, stage: str, name_hi: str) -> str:
    return f"🌧️ भारी बारिश ({rainfall}mm) आने वाली है। {name_hi} के खेत की नालियां साफ करें। आज सिंचाई बंद रखें।"

def _wind_advisory(crop: str, wind: float, stage: str, name_hi: str) -> str:
    return f"💨 तेज हवा चेतावनी ({wind} km/h)। आज कीटनाशक का छिड़काव बिल्कुल न करें। लंबी {name_hi} फसल को सहारा दें।"


def batch_classify(crop: str, growth_stage: str, daily_forecast: list) -> list:
    """Classify risks for multiple forecast days at once."""
    results = []
    for day in daily_forecast:
        result = classify_risk(
            crop=crop,
            growth_stage=growth_stage,
            temp_min_c=day.get("temp_min_c"),
            temp_max_c=day.get("temp_max_c"),
            rainfall_mm=day.get("rainfall_mm", 0),
            wind_kmh=day.get("wind_max_kmh", 0),
            rainfall_prob_pct=day.get("rainfall_prob_pct", 0)
        )
        result["date"] = day.get("date")
        results.append(result)
    return results


def classify_risk_translated(
    crop: str,
    growth_stage: str,
    temp_min_c: float,
    temp_max_c: float,
    rainfall_mm: float,
    wind_kmh: float,
    rainfall_prob_pct: float,
    language: str = "hi",
    soil_saturation_index: float = 0.5
) -> dict:
    """
    Same as classify_risk but returns advisory in requested language.
    """
    from utils.translations import get_translation

    try:
        profile = get_crop_profile(crop)
    except ValueError as e:
        return {"error": str(e)}

    risks = []
    crop_hi = profile["name_hi"]

    # Get crop name in requested language
    crop_name = get_crop_name(crop, language)

    # Get severity labels for requested language
    sev_labels = SEVERITY_LABELS_LANG.get(language, SEVERITY_LABELS_LANG["en"])

    # Heatwave
    if temp_max_c is not None and temp_max_c > profile["heatwave_temp_c"]:
        severity = _heat_severity(temp_max_c, profile["heatwave_temp_c"])
        advisory = get_translation(language, "heat_advisory",
                                   temp=temp_max_c, crop=crop_name)
        risks.append({
            "type": "heatwave",
            "severity": severity,
            "severity_label": sev_labels.get(severity, str(severity)),
            "detected_value": f"{temp_max_c}°C",
            "threshold": f"{profile['heatwave_temp_c']}°C",
            "advisory": advisory
        })

    # Frost
    if temp_min_c is not None and temp_min_c < profile["frost_risk_temp_c"]:
        severity = _frost_severity(temp_min_c, profile["frost_risk_temp_c"], growth_stage)
        advisory = get_translation(language, "frost_advisory",
                                   temp=temp_min_c, crop=crop_name)
        risks.append({
            "type": "frost",
            "severity": severity,
            "severity_label": sev_labels.get(severity, str(severity)),
            "detected_value": f"{temp_min_c}°C",
            "threshold": f"{profile['frost_risk_temp_c']}°C",
            "advisory": advisory
        })

    # Excess Rain
    if rainfall_mm is not None and rainfall_mm > profile["max_rain_mm_day"]:
        severity = _rain_severity(rainfall_mm, profile["max_rain_mm_day"])
        advisory = get_translation(language, "rain_advisory",
                                   rain=rainfall_mm, crop=crop_name)
        risks.append({
            "type": "excess_rain",
            "severity": severity,
            "severity_label": sev_labels.get(severity, str(severity)),
            "detected_value": f"{rainfall_mm}mm",
            "threshold": f"{profile['max_rain_mm_day']}mm",
            "advisory": advisory
        })

    # High Wind
    if wind_kmh is not None and wind_kmh > profile["wind_risk_kmh"]:
        severity = _wind_severity(wind_kmh, profile["wind_risk_kmh"])
        advisory = get_translation(language, "wind_advisory",
                                   wind=wind_kmh)
        risks.append({
            "type": "high_wind",
            "severity": severity,
            "severity_label": sev_labels.get(severity, str(severity)),
            "detected_value": f"{wind_kmh}km/h",
            "threshold": f"{profile['wind_risk_kmh']}km/h",
            "advisory": advisory
        })

    risks.sort(key=lambda x: x["severity"], reverse=True)
    max_severity = risks[0]["severity"] if risks else 0

    result = {
        "crop": crop,
        "crop_hi": crop_hi,
        "growth_stage": growth_stage,
        "risks": risks,
        "max_severity": max_severity,
        "max_severity_label": sev_labels.get(max_severity, "None"),
        "alert_required": max_severity >= 3,
        "emergency": max_severity >= 5,
        "total_risks_detected": len(risks),
        "language": language
    }

    if not risks:
        result["message"] = get_translation(language, "no_risk")

    return result