"""
MODULE — PDF Generator (ReportLab)
Generates multilingual 3-page weekly climate risk report for farmers.
PDF generated in memory — no disk storage used.
"""

import sys
sys.path.insert(0, '.')

import io
import os
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger("pdf_generator")

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
NOTO_SANS     = os.path.join(FONTS_DIR, "NotoSans-Regular.ttf")
NOTO_DEVA     = os.path.join(FONTS_DIR, "NotoSansDevanagari-Regular.ttf")
NOTO_GUJARATI = os.path.join(FONTS_DIR, "NotoSansGujarati-Regular.ttf")
NOTO_TAMIL    = os.path.join(FONTS_DIR, "NotoSansTamil-Regular.ttf")
NOTO_TELUGU   = os.path.join(FONTS_DIR, "NotoSansTelugu-Regular.ttf")
NOTO_KANNADA  = os.path.join(FONTS_DIR, "NotoSansKannada-Regular.ttf")
NOTO_BENGALI  = os.path.join(FONTS_DIR, "NotoSansBengali-Regular.ttf")
NOTO_GURMUKHI = os.path.join(FONTS_DIR, "NotoSansGurmukhi-Regular.ttf")

GREEN_DARK  = (26/255,  107/255, 60/255)
GREEN_MED   = (39/255,  174/255, 96/255)
GREEN_LIGHT = (240/255, 249/255, 244/255)
WHITE       = (1, 1, 1)
DARK        = (44/255,  62/255,  80/255)
GRAY        = (127/255, 140/255, 141/255)
LIGHT_GRAY  = (236/255, 240/255, 241/255)
YELLOW_BG   = (255/255, 249/255, 230/255)
BLUE_BG     = (234/255, 244/255, 251/255)
BLUE_DARK   = (36/255,  113/255, 163/255)
PINK_BG     = (253/255, 242/255, 248/255)
RED_DARK    = (146/255, 43/255,  33/255)

RISK_COLORS = {
    0: (39/255, 174/255, 96/255),  1: (39/255, 174/255, 96/255),
    2: (243/255, 156/255, 18/255), 3: (230/255, 126/255, 34/255),
    4: (231/255, 76/255,  60/255), 5: (146/255, 43/255,  33/255),
}
RISK_LABELS = {
    0: "Safe", 1: "Low Risk", 2: "Caution",
    3: "High Risk", 4: "Very High Risk", 5: "Critical"
}

LABELS = {
    "hi": {
        "title": "KisanMitra — साप्ताहिक कृषि रिपोर्ट",
        "farmer": "किसान", "id": "ID", "district": "जिला",
        "crop": "फसल", "field": "खेत", "stage": "अवस्था",
        "soil": "मिट्टी", "week": "सप्ताह", "language_name": "हिंदी",
        "weather": "मौसम सारांश", "min_temp": "न्यूनतम तापमान",
        "max_temp": "अधिकतम तापमान", "rainfall": "कुल वर्षा",
        "key_events": "मुख्य घटनाएं", "forecast": "7 दिन का पूर्वानुमान",
        "risk": "फसल जोखिम रिपोर्ट", "overall_risk": "इस सप्ताह का जोखिम",
        "lstm": "अगले सप्ताह वर्षा पूर्वानुमान (AI)",
        "irrigation": "सिंचाई अनुशंसा", "irr_days": "सिंचाई के दिन",
        "skip_days": "बंद के दिन", "total_water": "कुल पानी",
        "advisory": "AI सलाह — इस सप्ताह", "next_week": "अगले सप्ताह के लिए सुझाव",
        "emergency": "आपातकालीन संपर्क", "kisan_helpline": "किसान कॉल सेंटर",
        "generated": "KisanMitra AI द्वारा तैयार", "next_report": "अगली रिपोर्ट",
        "disclaimer": "यह रिपोर्ट उपग्रह मौसम डेटा पर आधारित है। स्थानीय विशेषज्ञों से परामर्श लें।",
        "date_col": "तारीख", "temp_col": "तापमान", "rain_col": "वर्षा",
        "wind_col": "हवा", "risk_col": "जोखिम", "reason_col": "कारण",
        "decision_col": "निर्णय", "liters_col": "पानी(L)",
        "irrigate": "सिंचाई करें", "skip": "बंद रखें", "reduce": "कम करें",
        "h24": "24 घंटे", "h48": "48 घंटे", "h72": "72 घंटे",
        "acres": "एकड़", "page": "पृष्ठ", "of": "का",
    },
    "mr": {
        "title": "KisanMitra — साप्ताहिक कृषी अहवाल",
        "farmer": "शेतकरी", "id": "ID", "district": "जिल्हा",
        "crop": "पीक", "field": "शेत", "stage": "अवस्था",
        "soil": "माती", "week": "आठवडा", "language_name": "मराठी",
        "weather": "हवामान सारांश", "min_temp": "किमान तापमान",
        "max_temp": "कमाल तापमान", "rainfall": "एकूण पाऊस",
        "key_events": "मुख्य घटना", "forecast": "७ दिवसांचा अंदाज",
        "risk": "पीक धोका अहवाल", "overall_risk": "या आठवड्याचा धोका",
        "lstm": "पुढील आठवडा पाऊस अंदाज (AI)",
        "irrigation": "सिंचन शिफारस", "irr_days": "सिंचन दिवस",
        "skip_days": "बंद दिवस", "total_water": "एकूण पाणी",
        "advisory": "AI सल्ला — या आठवड्यात", "next_week": "पुढील आठवड्यासाठी सूचना",
        "emergency": "आपत्कालीन संपर्क", "kisan_helpline": "किसान कॉल सेंटर",
        "generated": "KisanMitra AI द्वारे तयार", "next_report": "पुढील अहवाल",
        "disclaimer": "हा अहवाल उपग्रह हवामान डेटावर आधारित आहे।",
        "date_col": "तारीख", "temp_col": "तापमान", "rain_col": "पाऊस",
        "wind_col": "वारा", "risk_col": "धोका", "reason_col": "कारण",
        "decision_col": "निर्णय", "liters_col": "पाणी(L)",
        "irrigate": "सिंचन करा", "skip": "बंद ठेवा", "reduce": "कमी करा",
        "h24": "24 तास", "h48": "48 तास", "h72": "72 तास",
        "acres": "एकर", "page": "पृष्ठ", "of": "चा",
    },
    "en": {
        "title": "KisanMitra — Weekly Agricultural Report",
        "farmer": "Farmer", "id": "ID", "district": "District",
        "crop": "Crop", "field": "Field", "stage": "Stage",
        "soil": "Soil", "week": "Week", "language_name": "English",
        "weather": "Weather Summary", "min_temp": "Min Temp",
        "max_temp": "Max Temp", "rainfall": "Total Rainfall",
        "key_events": "Key Events", "forecast": "7-Day Forecast",
        "risk": "Crop Risk Report", "overall_risk": "This Week Risk Level",
        "lstm": "Next Week Rainfall Prediction (AI)",
        "irrigation": "Irrigation Recommendation", "irr_days": "Irrigate Days",
        "skip_days": "Skip Days", "total_water": "Total Water",
        "advisory": "AI Advisory — This Week", "next_week": "Tips for Next Week",
        "emergency": "Emergency Contact", "kisan_helpline": "Kisan Call Center",
        "generated": "Generated by KisanMitra AI", "next_report": "Next Report",
        "disclaimer": "This report is based on satellite weather data. Consult local experts.",
        "date_col": "Date", "temp_col": "Temp", "rain_col": "Rain",
        "wind_col": "Wind", "risk_col": "Risk", "reason_col": "Reason",
        "decision_col": "Decision", "liters_col": "Water(L)",
        "irrigate": "Irrigate", "skip": "Skip", "reduce": "Reduce",
        "h24": "24h", "h48": "48h", "h72": "72h",
        "acres": "acres", "page": "Page", "of": "of",
    },
}

# Kannada
LABELS["kn"] = LABELS["en"].copy()
LABELS["kn"].update({
    "language_name": "Kannada",
    "title": "KisanMitra — ವಾರದ ಕೃಷಿ ವರದಿ",
    "farmer": "ರೈತ", "district": "ಜಿಲ್ಲೆ", "crop": "ಬೆಳೆ",
    "field": "ಜಮೀನು", "stage": "ಹಂತ", "soil": "ಮಣ್ಣು", "week": "ವಾರ",
    "weather": "ಹವಾಮಾನ ಸಾರಾಂಶ", "min_temp": "ಕನಿಷ್ಠ ತಾಪಮಾನ",
    "max_temp": "ಗರಿಷ್ಠ ತಾಪಮಾನ", "rainfall": "ಒಟ್ಟು ಮಳೆ",
    "key_events": "ಪ್ರಮುಖ ಘಟನೆಗಳು", "forecast": "7 ದಿನಗಳ ಮುನ್ಸೂಚನೆ",
    "risk": "ಬೆಳೆ ಅಪಾಯ ವರದಿ", "overall_risk": "ಈ ವಾರದ ಅಪಾಯ",
    "lstm": "ಮುಂದಿನ ವಾರ ಮಳೆ ಮುನ್ಸೂಚನೆ (AI)",
    "irrigation": "ನೀರಾವರಿ ಶಿಫಾರಸು", "irr_days": "ನೀರಾವರಿ ದಿನಗಳು",
    "skip_days": "ಬಿಟ್ಟ ದಿನಗಳು", "total_water": "ಒಟ್ಟು ನೀರು",
    "advisory": "AI ಸಲಹೆ — ಈ ವಾರ", "next_week": "ಮುಂದಿನ ವಾರದ ಸಲಹೆ",
    "disclaimer": "ಈ ವರದಿ ಉಪಗ್ರಹ ಹವಾಮಾನ ಡೇಟಾ ಆಧಾರಿತವಾಗಿದೆ.",
    "date_col": "ದಿನಾಂಕ", "temp_col": "ತಾಪಮಾನ", "rain_col": "ಮಳೆ",
    "wind_col": "ಗಾಳಿ", "risk_col": "ಅಪಾಯ", "reason_col": "ಕಾರಣ",
    "decision_col": "ನಿರ್ಧಾರ", "liters_col": "ನೀರು(L)",
    "irrigate": "ನೀರಾವರಿ ಮಾಡಿ", "skip": "ಬಿಡಿ", "reduce": "ಕಡಿಮೆ ಮಾಡಿ",
    "h24": "24 ಗಂಟೆ", "h48": "48 ಗಂಟೆ", "h72": "72 ಗಂಟೆ",
    "acres": "ಎಕರೆ", "page": "ಪುಟ", "of": "ರಲ್ಲಿ",
    "generated": "KisanMitra AI ರಿಂದ ರಚಿಸಲಾಗಿದೆ", "next_report": "ಮುಂದಿನ ವರದಿ",
})

# Telugu
LABELS["te"] = LABELS["en"].copy()
LABELS["te"].update({
    "language_name": "Telugu",
    "title": "KisanMitra — వారపు వ్యవసాయ నివేదిక",
    "farmer": "రైతు", "district": "జిల్లా", "crop": "పంట",
    "field": "పొలం", "stage": "దశ", "soil": "నేల", "week": "వారం",
    "weather": "వాతావరణ సారాంశం", "min_temp": "కనిష్ట ఉష్ణోగ్రత",
    "max_temp": "గరిష్ట ఉష్ణోగ్రత", "rainfall": "మొత్తం వర్షపాతం",
    "key_events": "ముఖ్య సంఘటనలు", "forecast": "7 రోజుల అంచనా",
    "risk": "పంట రిస్క్ నివేదిక", "overall_risk": "ఈ వారం రిస్క్",
    "lstm": "వచ్చే వారం వర్షపాతం అంచనా (AI)",
    "irrigation": "నీటిపారుదల సిఫార్సు", "irr_days": "నీటిపారుదల రోజులు",
    "skip_days": "వదిలిన రోజులు", "total_water": "మొత్తం నీరు",
    "advisory": "AI సలహా — ఈ వారం", "next_week": "వచ్చే వారం చిట్కాలు",
    "disclaimer": "ఈ నివేదిక ఉపగ్రహ వాతావరణ డేటా ఆధారంగా ఉంది.",
    "date_col": "తేదీ", "temp_col": "ఉష్ణోగ్రత", "rain_col": "వర్షం",
    "wind_col": "గాలి", "risk_col": "రిస్క్", "reason_col": "కారణం",
    "decision_col": "నిర్ణయం", "liters_col": "నీరు(L)",
    "irrigate": "నీరు పెట్టండి", "skip": "వదలండి", "reduce": "తగ్గించండి",
    "h24": "24 గంటలు", "h48": "48 గంటలు", "h72": "72 గంటలు",
    "acres": "ఎకరాలు", "page": "పేజీ", "of": "లో",
    "generated": "KisanMitra AI రూపొందించింది", "next_report": "తదుపరి నివేదిక",
})

# Tamil
LABELS["ta"] = LABELS["en"].copy()
LABELS["ta"].update({
    "language_name": "Tamil",
    "title": "KisanMitra — வாராந்திர வேளாண் அறிக்கை",
    "farmer": "விவசாயி", "district": "மாவட்டம்", "crop": "பயிர்",
    "field": "வயல்", "stage": "நிலை", "soil": "மண்", "week": "வாரம்",
    "weather": "வானிலை சுருக்கம்", "min_temp": "குறைந்த வெப்பநிலை",
    "max_temp": "அதிக வெப்பநிலை", "rainfall": "மொத்த மழை",
    "key_events": "முக்கிய நிகழ்வுகள்", "forecast": "7 நாள் முன்னறிவிப்பு",
    "risk": "பயிர் அபாய அறிக்கை", "overall_risk": "இந்த வார அபாயம்",
    "lstm": "அடுத்த வார மழை முன்னறிவிப்பு (AI)",
    "irrigation": "நீர்ப்பாசன பரிந்துரை", "irr_days": "நீர்ப்பாசன நாட்கள்",
    "skip_days": "தவிர்த்த நாட்கள்", "total_water": "மொத்த நீர்",
    "advisory": "AI ஆலோசனை — இந்த வாரம்", "next_week": "அடுத்த வார குறிப்புகள்",
    "disclaimer": "இந்த அறிக்கை செயற்கைக்கோள் தரவை அடிப்படையாகக் கொண்டது.",
    "date_col": "தேதி", "temp_col": "வெப்பம்", "rain_col": "மழை",
    "wind_col": "காற்று", "risk_col": "அபாயம்", "reason_col": "காரணம்",
    "decision_col": "முடிவு", "liters_col": "நீர்(L)",
    "irrigate": "நீர் பாய்ச்சுங்கள்", "skip": "தவிர்க்கவும்", "reduce": "குறைக்கவும்",
    "h24": "24 மணி", "h48": "48 மணி", "h72": "72 மணி",
    "acres": "ஏக்கர்", "page": "பக்கம்", "of": "இல்",
    "generated": "KisanMitra AI உருவாக்கியது", "next_report": "அடுத்த அறிக்கை",
})

# Punjabi
LABELS["pa"] = LABELS["en"].copy()
LABELS["pa"].update({
    "language_name": "Punjabi",
    "title": "KisanMitra — ਹਫ਼ਤਾਵਾਰੀ ਖੇਤੀ ਰਿਪੋਰਟ",
    "farmer": "ਕਿਸਾਨ", "district": "ਜ਼ਿਲ੍ਹਾ", "crop": "ਫ਼ਸਲ",
    "field": "ਖੇਤ", "stage": "ਅਵਸਥਾ", "soil": "ਮਿੱਟੀ", "week": "ਹਫ਼ਤਾ",
    "weather": "ਮੌਸਮ ਸਾਰਾਂਸ਼", "min_temp": "ਘੱਟੋ-ਘੱਟ ਤਾਪਮਾਨ",
    "max_temp": "ਵੱਧ ਤੋਂ ਵੱਧ ਤਾਪਮਾਨ", "rainfall": "ਕੁੱਲ ਵਰਖਾ",
    "key_events": "ਮੁੱਖ ਘਟਨਾਵਾਂ", "forecast": "7 ਦਿਨਾਂ ਦਾ ਅਨੁਮਾਨ",
    "risk": "ਫ਼ਸਲ ਖ਼ਤਰਾ ਰਿਪੋਰਟ", "overall_risk": "ਇਸ ਹਫ਼ਤੇ ਦਾ ਖ਼ਤਰਾ",
    "lstm": "ਅਗਲੇ ਹਫ਼ਤੇ ਵਰਖਾ ਅਨੁਮਾਨ (AI)",
    "irrigation": "ਸਿੰਚਾਈ ਸਿਫ਼ਾਰਸ਼", "irr_days": "ਸਿੰਚਾਈ ਦਿਨ",
    "skip_days": "ਬੰਦ ਦਿਨ", "total_water": "ਕੁੱਲ ਪਾਣੀ",
    "advisory": "AI ਸਲਾਹ — ਇਸ ਹਫ਼ਤੇ", "next_week": "ਅਗਲੇ ਹਫ਼ਤੇ ਲਈ ਸੁਝਾਅ",
    "disclaimer": "ਇਹ ਰਿਪੋਰਟ ਉਪਗ੍ਰਹਿ ਮੌਸਮ ਡੇਟਾ 'ਤੇ ਆਧਾਰਿਤ ਹੈ।",
    "date_col": "ਤਾਰੀਖ਼", "temp_col": "ਤਾਪਮਾਨ", "rain_col": "ਵਰਖਾ",
    "wind_col": "ਹਵਾ", "risk_col": "ਖ਼ਤਰਾ", "reason_col": "ਕਾਰਨ",
    "decision_col": "ਫ਼ੈਸਲਾ", "liters_col": "ਪਾਣੀ(L)",
    "irrigate": "ਸਿੰਚਾਈ ਕਰੋ", "skip": "ਬੰਦ ਰੱਖੋ", "reduce": "ਘੱਟ ਕਰੋ",
    "h24": "24 ਘੰਟੇ", "h48": "48 ਘੰਟੇ", "h72": "72 ਘੰਟੇ",
    "acres": "ਏਕੜ", "page": "ਪੰਨਾ", "of": "ਦਾ",
    "generated": "KisanMitra AI ਦੁਆਰਾ ਤਿਆਰ", "next_report": "ਅਗਲੀ ਰਿਪੋਰਟ",
})

# Bengali
LABELS["bn"] = LABELS["en"].copy()
LABELS["bn"].update({
    "language_name": "Bengali",
    "title": "KisanMitra — সাপ্তাহিক কৃষি রিপোর্ট",
    "farmer": "কৃষক", "district": "জেলা", "crop": "ফসল",
    "field": "জমি", "stage": "পর্যায়", "soil": "মাটি", "week": "সপ্তাহ",
    "weather": "আবহাওয়া সারসংক্ষেপ", "min_temp": "সর্বনিম্ন তাপমাত্রা",
    "max_temp": "সর্বোচ্চ তাপমাত্রা", "rainfall": "মোট বৃষ্টিপাত",
    "key_events": "প্রধান ঘটনাসমূহ", "forecast": "৭ দিনের পূর্বাভাস",
    "risk": "ফসল ঝুঁকি রিপোর্ট", "overall_risk": "এই সপ্তাহের ঝুঁকি",
    "lstm": "পরবর্তী সপ্তাহ বৃষ্টি পূর্বাভাস (AI)",
    "irrigation": "সেচ সুপারিশ", "irr_days": "সেচ দিন",
    "skip_days": "বাদ দিন", "total_water": "মোট পানি",
    "advisory": "AI পরামর্শ — এই সপ্তাহ", "next_week": "আগামী সপ্তাহের পরামর্শ",
    "disclaimer": "এই রিপোর্ট স্যাটেলাইট আবহাওয়া ডেটার উপর ভিত্তি করে।",
    "date_col": "তারিখ", "temp_col": "তাপমাত্রা", "rain_col": "বৃষ্টি",
    "wind_col": "বায়ু", "risk_col": "ঝুঁকি", "reason_col": "কারণ",
    "decision_col": "সিদ্ধান্ত", "liters_col": "পানি(L)",
    "irrigate": "সেচ দিন", "skip": "বাদ দিন", "reduce": "কমান",
    "h24": "২৪ ঘণ্টা", "h48": "৪৮ ঘণ্টা", "h72": "৭২ ঘণ্টা",
    "acres": "একর", "page": "পাতা", "of": "এর",
    "generated": "KisanMitra AI দ্বারা তৈরি", "next_report": "পরবর্তী রিপোর্ট",
})

# Gujarati
LABELS["gu"] = LABELS["en"].copy()
LABELS["gu"].update({
    "language_name": "Gujarati",
    "title": "KisanMitra — સાપ્તાહિક કૃષિ અહેવાલ",
    "farmer": "ખેડૂત", "district": "જિલ્લો", "crop": "પાક",
    "field": "ખેતર", "stage": "તબક્કો", "soil": "માટી", "week": "અઠવાડિયું",
    "weather": "હવામાન સારાંશ", "min_temp": "ન્યૂનતમ તાપમાન",
    "max_temp": "મહત્તમ તાપમાન", "rainfall": "કુલ વરસાદ",
    "key_events": "મુખ્ય ઘટનાઓ", "forecast": "7 દિવસની આગાહી",
    "risk": "પાક જોખમ અહેવાલ", "overall_risk": "આ અઠવાડિયાનું જોખમ",
    "lstm": "આગામી અઠવાડિયે વરસાદ આગાહી (AI)",
    "irrigation": "સિંચાઈ ભલામણ", "irr_days": "સિંચાઈ દિવસો",
    "skip_days": "બંધ દિવસો", "total_water": "કુલ પાણી",
    "advisory": "AI સલાહ — આ અઠવાડિયે", "next_week": "આગામી અઠવાડિયા માટે સૂચનો",
    "disclaimer": "આ અહેવાલ સેટેલાઇટ હવામાન ડેટા પર આધારિત છે.",
    "date_col": "તારીખ", "temp_col": "તાપમાન", "rain_col": "વરસાદ",
    "wind_col": "પવન", "risk_col": "જોખમ", "reason_col": "કારણ",
    "decision_col": "નિર્ણય", "liters_col": "પાણી(L)",
    "irrigate": "સિંચાઈ કરો", "skip": "બંધ રાખો", "reduce": "ઓછું કરો",
    "h24": "24 કલાક", "h48": "48 કલાક", "h72": "72 કલાક",
    "acres": "એકર", "page": "પૃષ્ઠ", "of": "નો",
    "generated": "KisanMitra AI દ્વારા તૈયાર", "next_report": "આગામી અહેવાલ",
})

CROP_NAMES = {
    "wheat":     {"hi":"गेहूं","mr":"गहू","en":"Wheat","kn":"Wheat","te":"Wheat","ta":"Wheat","pa":"Wheat","bn":"গম","gu":"ઘઉં"},
    "rice":      {"hi":"चावल","mr":"तांदूळ","en":"Rice","kn":"Rice","te":"Rice","ta":"Rice","pa":"Rice","bn":"ধান","gu":"ચોખા"},
    "soybean":   {"hi":"सोयाबीन","mr":"सोयाबीन","en":"Soybean","kn":"Soybean","te":"Soybean","ta":"Soybean","pa":"Soybean","bn":"সয়াবিন","gu":"સોયાબીન"},
    "cotton":    {"hi":"कपास","mr":"कापूस","en":"Cotton","kn":"Cotton","te":"Cotton","ta":"Cotton","pa":"Cotton","bn":"তুলা","gu":"કપાસ"},
    "sugarcane": {"hi":"गन्ना","mr":"ऊस","en":"Sugarcane","kn":"Sugarcane","te":"Sugarcane","ta":"Sugarcane","pa":"Sugarcane","bn":"আখ","gu":"શેરડી"},
    "onion":     {"hi":"प्याज","mr":"कांदा","en":"Onion","kn":"Onion","te":"Onion","ta":"Onion","pa":"Onion","bn":"পেঁয়াজ","gu":"ડુંગળી"},
    "tomato":    {"hi":"टमाटर","mr":"टोमॅटो","en":"Tomato","kn":"Tomato","te":"Tomato","ta":"Tomato","pa":"Tomato","bn":"টমেটো","gu":"ટામેટું"},
}


def _download_fonts_if_needed():
    """Download missing fonts from system or PyPI package."""
    import subprocess
    for fname in ["NotoSansGujarati-Regular.ttf", "NotoSansTamil-Regular.ttf",
                  "NotoSansTelugu-Regular.ttf", "NotoSansKannada-Regular.ttf",
                  "NotoSansBengali-Regular.ttf", "NotoSansGurmukhi-Regular.ttf"]:
        dest = os.path.join(FONTS_DIR, fname)
        if not os.path.exists(dest) or os.path.getsize(dest) < 1000:
            # Try system fonts first
            system_path = f"/usr/share/fonts/truetype/noto/{fname}"
            if os.path.exists(system_path) and os.path.getsize(system_path) > 1000:
                import shutil
                shutil.copy(system_path, dest)
                logger.info(f"Copied font from system: {fname}")
            else:
                # Try apt install
                try:
                    subprocess.run(["apt-get", "install", "-y", "fonts-noto"],
                                   capture_output=True, timeout=60)
                    if os.path.exists(system_path) and os.path.getsize(system_path) > 1000:
                        import shutil
                        shutil.copy(system_path, dest)
                        logger.info(f"Installed and copied: {fname}")
                except Exception as e:
                    logger.warning(f"Could not install font {fname}: {e}")

def _register_fonts():
    _download_fonts_if_needed()
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font_map = {
        "NotoSans":         NOTO_SANS,
        "NotoSansDevanagari": NOTO_DEVA,
        "NotoSansGujarati": NOTO_GUJARATI,
        "NotoSansTamil":    NOTO_TAMIL,
        "NotoSansTelugu":   NOTO_TELUGU,
        "NotoSansKannada":  NOTO_KANNADA,
        "NotoSansBengali":  NOTO_BENGALI,
        "NotoSansGurmukhi": NOTO_GURMUKHI,
    }
    for name, path in font_map.items():
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass


def _font(language: str) -> str:
    """Get primary font for language - each script needs its own font."""
    font_map = {
        "hi": ("NotoSansDevanagari", NOTO_DEVA),
        "mr": ("NotoSansDevanagari", NOTO_DEVA),
        "gu": ("NotoSansGujarati",   NOTO_GUJARATI),
        "ta": ("NotoSansTamil",      NOTO_TAMIL),
        "te": ("NotoSansTelugu",     NOTO_TELUGU),
        "kn": ("NotoSansKannada",    NOTO_KANNADA),
        "bn": ("NotoSansBengali",    NOTO_BENGALI),
        "pa": ("NotoSansGurmukhi",   NOTO_GURMUKHI),
        "en": ("NotoSans",           NOTO_SANS),
    }
    name, path = font_map.get(language, ("NotoSans", NOTO_SANS))
    if os.path.exists(path):
        return name
    if os.path.exists(NOTO_SANS):
        return "NotoSans"
    return "Helvetica"


def _ascii_font() -> str:
    """Always use NotoSans for ASCII/English text."""
    if os.path.exists(NOTO_SANS):
        return "NotoSans"
    return "Helvetica"


def _weather_tag(temp, rain, wind) -> str:
    if rain > 30: return "Heavy Rain"
    if rain > 10: return "Showers"
    if wind > 50: return "Windy"
    if temp > 42: return "Extreme Heat"
    if temp > 35: return "Sunny Hot"
    if temp < 10: return "Cold"
    return "Clear"


def _draw_header(c, W, H, farmer, language, week_num, now, L, font):
    from reportlab.lib.units import mm
    afont = _ascii_font()

    c.setFillColorRGB(*GREEN_DARK)
    c.rect(0, H - 55*mm, W, 55*mm, fill=1, stroke=0)

    c.setFillColorRGB(*WHITE)
    c.setFont(afont, 18)
    c.drawString(14*mm, H - 13*mm, "* KisanMitra")
    # Title uses language font, but fallback to afont if title is ASCII
    try:
        L["title"].encode('ascii')
        c.setFont(afont, 9)
    except (UnicodeEncodeError, UnicodeDecodeError):
        c.setFont(font, 9)
    c.drawString(14*mm, H - 19*mm, L["title"])

    c.setFillColorRGB(1,1,1,0.2)
    c.roundRect(W-48*mm, H-22*mm, 34*mm, 14*mm, 5, fill=1, stroke=0)
    c.setFillColorRGB(*WHITE)
    c.setFont(afont, 8)
    c.drawCentredString(W-31*mm, H-14*mm, f"Week {week_num}")
    c.drawCentredString(W-31*mm, H-19*mm, now.strftime("%d %b %Y"))

    crop_name = CROP_NAMES.get(farmer.get("crop","wheat"),{}).get(language, farmer.get("crop","").capitalize())
    crop_en   = farmer.get("crop","wheat").capitalize()

    items = [
        (L["farmer"],  farmer.get("name",""),                                          True),
        (L["id"],      farmer.get("farmer_id",""),                                     True),
        (L["district"],f"{farmer.get('district','')}, {farmer.get('state','')}",  True),
        (L["crop"],    f"{crop_en}",                                                    True),
        (L["stage"],   f"{farmer.get('growth_stage','').capitalize()} | {farmer.get('soil_type','').capitalize()}", True),
        (L["field"],   f"{farmer.get('field_area_acres',1)} {L['acres']}",           True),
    ]

    bw = (W - 28*mm) / 3
    bh = 10*mm
    y0 = H - 32*mm

    for i, (lbl, val, use_ascii) in enumerate(items):
        col = i % 3
        row = i // 3
        bx  = 14*mm + col * bw
        by  = y0 - row * (bh + 1.5*mm)
        c.setFillColorRGB(1,1,1,0.15)
        c.roundRect(bx, by - bh + 2*mm, bw - 2*mm, bh, 3, fill=1, stroke=0)
        c.setFillColorRGB(1,1,1,0.7)
        # Label (like FARMER, ID etc) - use language font if non-ASCII
        lbl_str = str(lbl).upper()[:20]
        try:
            lbl_str.encode('ascii')
            c.setFont(afont, 6)
        except (UnicodeEncodeError, UnicodeDecodeError):
            c.setFont(font, 5)
        c.drawString(bx + 2*mm, by - 2.5*mm, lbl_str)
        c.setFillColorRGB(*WHITE)
        c.setFont(afont, 8)
        c.drawString(bx + 2*mm, by - 7.5*mm, str(val)[:34])


def _section(c, x, y, w, title, font):
    from reportlab.lib.units import mm
    c.setFillColorRGB(*GREEN_DARK)
    try:
        title.encode('ascii')
        c.setFont(font, 11)
    except (UnicodeEncodeError, UnicodeDecodeError):
        c.setFont(font, 10)
    c.drawString(x, y, title)
    c.setStrokeColorRGB(*GREEN_MED)
    c.setLineWidth(1.5)
    c.line(x, y-1.5*mm, x+w, y-1.5*mm)


def _table(c, x, y, data, col_w, font, rh=6.5):
    from reportlab.lib.units import mm
    hdrs = data[0]
    rows = data[1:]
    cx = x
    c.setFillColorRGB(*GREEN_DARK)
    c.rect(x, y-rh*mm, sum(col_w)*mm, rh*mm, fill=1, stroke=0)
    c.setFillColorRGB(*WHITE)
    c.setFont(font, 6.5)
    for h, w in zip(hdrs, col_w):
        c.drawString(cx+1.5*mm, y-(rh-1.5)*mm, str(h)[:18])
        cx += w*mm
    afont = _ascii_font()
    for ri, row in enumerate(rows):
        ry = y - (ri+2)*rh*mm
        if ri % 2 == 0:
            c.setFillColorRGB(*GREEN_LIGHT)
            c.rect(x, ry-0.5*mm, sum(col_w)*mm, rh*mm, fill=1, stroke=0)
        cx = x
        c.setFillColorRGB(*DARK)
        for val, w in zip(row, col_w):
            # Use language font for non-ASCII, ascii font for numbers/dates
            val_str = str(val)[:20]
            try:
                val_str.encode('ascii')
                c.setFont(afont, 7)
            except (UnicodeEncodeError, UnicodeDecodeError):
                c.setFont(font, 6)
            c.drawString(cx+1.5*mm, ry+(rh-4)*mm, val_str)
            cx += w*mm
        c.setStrokeColorRGB(*LIGHT_GRAY)
        c.setLineWidth(0.3)
        c.line(x, ry-0.5*mm, x+sum(col_w)*mm, ry-0.5*mm)
    return y - (len(data)+1)*rh*mm


def generate_pdf(farmer: dict, weather: dict, risks: list, irrigation: dict,
                 lstm_pred: dict, advisory: str, language: str = "hi") -> bytes:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    _register_fonts()
    font = _font(language)
    L    = LABELS.get(language, LABELS["en"])

    buf = io.BytesIO()
    W, H = A4
    c    = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"KisanMitra Report - {farmer.get('name','')}")
    afont = _ascii_font()  # For numbers, dates, English text

    daily    = weather.get("daily_forecast", [])
    schedule = irrigation.get("schedule", [])
    now      = datetime.now()
    wk       = now.isocalendar()[1]
    next_dt  = (now + timedelta(days=7)).strftime("%d %b %Y")
    mg       = 14*mm
    cw       = W - 2*mg

    # ───────── PAGE 1 ─────────
    _draw_header(c, W, H, farmer, language, wk, now, L, font)
    y = H - 60*mm

    c.setFillColorRGB(*GRAY); c.setFont(font,7)
    c.drawRightString(W-mg, 8*mm, f"{L['page']} 1 {L['of']} 3")

    # Weather stats
    y -= 6*mm
    _section(c, mg, y, cw, f"  {L['weather']}", font)
    y -= 8*mm

    temps = [d.get("temp_max_c",0) for d in daily]
    rains = [d.get("rainfall_mm",0) for d in daily]
    mn    = min([d.get("temp_min_c",0) for d in daily], default=0)
    mx    = max(temps, default=0)
    tr    = sum(rains)

    card_w3 = cw / 3
    for i,(val,lbl) in enumerate([(f"{mn:.0f}°C",L["min_temp"]),(f"{mx:.0f}°C",L["max_temp"]),(f"{tr:.0f}mm",L["rainfall"])]):
        cx = mg + i*card_w3
        c.setFillColorRGB(*GREEN_LIGHT)
        c.roundRect(cx+1*mm, y-14*mm, card_w3-2*mm, 14*mm, 4, fill=1, stroke=0)
        c.setFillColorRGB(*GREEN_DARK); c.setFont(afont,14)
        c.drawCentredString(cx+card_w3/2, y-8*mm, val)
        c.setFillColorRGB(*GRAY); c.setFont(font,7)
        c.drawCentredString(cx+card_w3/2, y-13*mm, lbl)
    y -= 18*mm

    # Key events
    events = []
    for d in daily:
        dt = d.get("date","")[:10]
        if d.get("temp_max_c",0) > 42: events.append(f"Heatwave {dt}: {d['temp_max_c']:.0f}C")
        if d.get("rainfall_mm",0) > 50: events.append(f"Heavy Rain {dt}: {d['rainfall_mm']:.0f}mm")
        if d.get("wind_max_kmh",0) > 60: events.append(f"Strong Wind {dt}: {d['wind_max_kmh']:.0f}km/h")
    if not events: events = ["No extreme weather events this week"]

    eh = (len(events)*5+8)*mm
    c.setFillColorRGB(*YELLOW_BG)
    c.roundRect(mg, y-eh, cw, eh, 4, fill=1, stroke=0)
    c.setStrokeColorRGB(243/255,156/255,18/255); c.setLineWidth(2)
    c.line(mg, y-eh, mg, y)
    c.setFillColorRGB(*DARK); c.setFont(font,8)
    c.drawString(mg+3*mm, y-5*mm, f"{L['key_events']}:")
    c.setFont(afont,7.5)
    for i,ev in enumerate(events):
        c.drawString(mg+5*mm, y-(10+i*5)*mm, ev)
    y -= eh+8*mm

    # Forecast table
    y -= 4*mm
    _section(c, mg, y, cw, f"  {L['forecast']}", font)
    y -= 4*mm
    ftable = [[L["date_col"],"Weather",f"{L['temp_col']} Max",f"{L['temp_col']} Min",f"{L['rain_col']}mm",f"{L['wind_col']}km/h"]]
    for d in daily:
        ftable.append([d.get("date","")[:10],
            _weather_tag(d.get("temp_max_c",0),d.get("rainfall_mm",0),d.get("wind_max_kmh",0)),
            f"{d.get('temp_max_c',0):.1f}C", f"{d.get('temp_min_c',0):.1f}C",
            f"{d.get('rainfall_mm',0):.1f}", f"{d.get('wind_max_kmh',0):.1f}"])
    _table(c, mg, y, ftable, [26,22,22,22,20,22], font)
    c.showPage()

    # ───────── PAGE 2 ─────────
    _draw_header(c, W, H, farmer, language, wk, now, L, font)
    y = H - 60*mm
    c.setFillColorRGB(*GRAY); c.setFont(font,7)
    c.drawRightString(W-mg, 8*mm, f"{L['page']} 2 {L['of']} 3")

    sevs   = [r.get("max_severity",0) for r in risks]
    o_sev  = max(sevs, default=0)
    r_col  = RISK_COLORS.get(o_sev, GREEN_MED)
    r_lbl  = RISK_LABELS.get(o_sev, "Safe")

    y -= 6*mm
    _section(c, mg, y, cw, f"  {L['risk']}", font)
    y -= 8*mm
    bw2 = 60*mm; bx2 = W/2-bw2/2
    c.setFillColorRGB(*r_col)
    c.roundRect(bx2, y-12*mm, bw2, 12*mm, 6, fill=1, stroke=0)
    c.setFillColorRGB(*WHITE); c.setFont(font,13)
    c.drawCentredString(W/2, y-8*mm, r_lbl)
    c.setFillColorRGB(*GRAY); c.setFont(font,7)
    c.drawCentredString(W/2, y-13.5*mm, L["overall_risk"])
    y -= 18*mm

    rtable = [[L["date_col"],L["risk_col"],L["reason_col"]]]
    for r in risks:
        sev = r.get("max_severity",0)
        reason = r["risks"][0].get("type","").replace("_"," ").capitalize() if r.get("risks") else "No risk"
        rtable.append([r.get("date","")[:10], RISK_LABELS.get(sev,"Safe"), reason])
    y -= 4*mm
    _table(c, mg, y, rtable, [33,44,57], font)
    y -= (len(rtable)+1)*6.5*mm+8*mm

    # LSTM
    _section(c, mg, y, cw, f"  {L['lstm']}", font)
    y -= 8*mm
    for i,(rain,prob,lbl) in enumerate([
        (f"{lstm_pred.get('rainfall_mm_24h',0):.1f}mm", f"{int(lstm_pred.get('probability_24h',0)*100)}%", L["h24"]),
        (f"{lstm_pred.get('rainfall_mm_48h',0):.1f}mm", f"{int(lstm_pred.get('probability_48h',0)*100)}%", L["h48"]),
        (f"{lstm_pred.get('rainfall_mm_72h',0):.1f}mm", f"{int(lstm_pred.get('probability_72h',0)*100)}%", L["h72"]),
    ]):
        cx = mg + i*card_w3
        c.setFillColorRGB(*BLUE_BG)
        c.roundRect(cx+1*mm, y-16*mm, card_w3-2*mm, 16*mm, 4, fill=1, stroke=0)
        c.setFillColorRGB(*BLUE_DARK); c.setFont(afont,14)
        c.drawCentredString(cx+card_w3/2, y-8*mm, rain)
        c.setFont(afont,8)
        c.drawCentredString(cx+card_w3/2, y-12.5*mm, f"Chance: {prob}")
        c.setFillColorRGB(*GRAY); c.setFont(afont,7)
        c.drawCentredString(cx+card_w3/2, y-15.5*mm, ["24h","48h","72h"][i])
    y -= 20*mm

    # Irrigation
    y -= 4*mm
    _section(c, mg, y, cw, f"  {L['irrigation']}", font)
    y -= 4*mm
    itbl = [[L["date_col"],L["decision_col"],L["liters_col"],L["reason_col"]]]
    ird = skd = totl = 0
    for s in schedule:
        dec = s.get("decision","")
        vol = s.get("volume_liters",0)
        if dec=="IRRIGATE": ird+=1
        elif dec=="SKIP": skd+=1
        totl += vol
        dl = L.get("irrigate" if dec=="IRRIGATE" else "skip" if dec=="SKIP" else "reduce", dec)
        itbl.append([s.get("date","")[:10], dl, f"{vol:.0f}L", s.get("reason","")[:26]])
    _table(c, mg, y, itbl, [26,24,20,64], font)
    y -= (len(itbl)+1)*6.5*mm+8*mm

    for i,(val,lbl) in enumerate([(str(ird),L["irr_days"]),(str(skd),L["skip_days"]),(f"{totl:.0f}L",L["total_water"])]):
        cx = mg + i*card_w3
        c.setFillColorRGB(*GREEN_LIGHT)
        c.roundRect(cx+1*mm, y-13*mm, card_w3-2*mm, 13*mm, 4, fill=1, stroke=0)
        c.setFillColorRGB(*GREEN_DARK); c.setFont(afont,14)
        c.drawCentredString(cx+card_w3/2, y-8*mm, val)
        c.setFillColorRGB(*GRAY); c.setFont(font,7)
        c.drawCentredString(cx+card_w3/2, y-12*mm, lbl)
    c.showPage()

    # ───────── PAGE 3 ─────────
    _draw_header(c, W, H, farmer, language, wk, now, L, font)
    y = H - 60*mm
    c.setFillColorRGB(*GRAY); c.setFont(font,7)
    c.drawRightString(W-mg, 8*mm, f"{L['page']} 3 {L['of']} 3")

    # Split advisory into lines, handle both newline and sentence endings
    adv_raw = []
    for line in advisory.split("\n"):
        line = line.strip()
        if line and len(line) > 5:
            adv_raw.append(line)
    
    # If less than 4 lines, split long lines into sentences
    if len(adv_raw) < 4:
        import re
        sentences = re.split(r'[।\.!]', advisory)
        adv_raw = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    adv_bullets = adv_raw[:4] or ["Monitor your crop daily", "Check weather updates", "Irrigate in morning", "Consult local Krishi Kendra"]
    next_tips   = adv_raw[4:6] if len(adv_raw) > 4 else ["Check weather forecast daily", "Consult local Krishi Kendra if needed"]

    y -= 6*mm
    _section(c, mg, y, cw, f"  {L['advisory']}", font)
    y -= 8*mm
    # Word wrap long advisory lines (Unicode-safe)
    def wrap_text(text, max_chars=40):
        """Unicode-safe wrap: use character count not byte count"""
        words = text.split()
        lines = []
        current = ""
        for word in words:
            # Use len() on string directly - Python 3 counts chars not bytes
            test = current + " " + word if current else word
            if len(test) <= max_chars:
                current = test
            else:
                if current:
                    lines.append(current)
                # If single word is too long, split it
                if len(word) > max_chars:
                    lines.append(word[:max_chars])
                    current = word[max_chars:]
                else:
                    current = word
        if current:
            lines.append(current)
        return lines if lines else [text[:max_chars]]

    # Expand bullets with wrapping
    expanded_bullets = []
    for b in adv_bullets:
        wrapped = wrap_text(b, 72)
        expanded_bullets.extend(wrapped[:3])  # max 3 lines per bullet

    abh = (len(expanded_bullets)*7+10)*mm
    c.setFillColorRGB(*GREEN_LIGHT)
    c.roundRect(mg, y-abh, cw, abh, 5, fill=1, stroke=0)
    c.setStrokeColorRGB(*GREEN_MED); c.setLineWidth(2)
    c.line(mg, y-abh, mg, y)
    c.setFillColorRGB(*DARK)
    bullet_y = y - 6*mm
    for i,line in enumerate(expanded_bullets):
        try:
            line.encode('ascii')
            c.setFont(afont, 8.5)
        except (UnicodeEncodeError, UnicodeDecodeError):
            c.setFont(font, 8)
        c.drawString(mg+5*mm, bullet_y, f"•  {line}")
        bullet_y -= 7*mm
    y -= abh+8*mm

    _section(c, mg, y, cw, f"  {L['next_week']}", font)
    y -= 8*mm
    expanded_tips = []
    for t in next_tips:
        wrapped = wrap_text(t, 72)
        expanded_tips.extend(wrapped[:3])

    nth = (len(expanded_tips)*7+10)*mm
    c.setFillColorRGB(*GREEN_LIGHT)
    c.roundRect(mg, y-nth, cw, nth, 5, fill=1, stroke=0)
    c.setFillColorRGB(*DARK)
    tip_y = y - 6*mm
    for line in expanded_tips:
        try:
            line.encode('ascii')
            c.setFont(afont, 8.5)
        except (UnicodeEncodeError, UnicodeDecodeError):
            c.setFont(font, 8)
        c.drawString(mg+5*mm, tip_y, f"->  {line}")
        tip_y -= 7*mm
    y -= nth+10*mm

    # Emergency
    c.setFillColorRGB(*PINK_BG)
    c.roundRect(mg, y-20*mm, cw, 20*mm, 5, fill=1, stroke=0)
    c.setFillColorRGB(*RED_DARK); c.setFont(font,9)
    c.drawString(mg+5*mm, y-7*mm, "Emergency Contact")
    c.setFont(afont,11)
    c.drawString(mg+5*mm, y-14*mm, "Kisan Call Center: 1800-180-1551")
    c.setFillColorRGB(*GRAY); c.setFont(afont,7)
    c.drawString(mg+5*mm, y-19*mm, "Toll Free  ·  24/7  ·  All Languages")
    y -= 28*mm

    # Footer
    c.setStrokeColorRGB(*LIGHT_GRAY); c.setLineWidth(0.5)
    c.line(mg, y, W-mg, y)
    y -= 5*mm
    c.setFillColorRGB(*GREEN_DARK); c.setFont(afont,9)
    c.drawString(mg, y, "  Generated by KisanMitra AI")
    c.setFillColorRGB(*GRAY); c.setFont(afont,8)
    c.drawRightString(W-mg, y, f"Next Report: {next_dt}")
    y -= 5*mm
    c.setFont(font,6.5)
    c.drawString(mg, y, L["disclaimer"])

    c.save()
    data = buf.getvalue()
    buf.close()
    logger.info(f"PDF: {farmer.get('farmer_id')} · {language} · {len(data)//1024}KB")
    return data


if __name__ == "__main__":
    print("Testing PDF generator...")

    dummy_farmer = {
        "farmer_id":"be15d001","name":"Ramesh Kumar",
        "district":"Indore","state":"Madhya Pradesh",
        "crop":"wheat","growth_stage":"vegetative",
        "field_area_acres":2.5,"soil_type":"loamy","language":"hi",
    }

    # Fixed dates using timedelta
    from datetime import date, timedelta as td
    base = date(2026, 4, 28)
    dates = [(base + td(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    dummy_weather = {"daily_forecast":[
        {"date":dates[i],"temp_max_c":43-i,"temp_min_c":27-i,
         "rainfall_mm":[0,0,5,10,2,0,0][i],"wind_max_kmh":[20,18,25,30,20,15,18][i],
         "rainfall_prob_pct":[10,15,30,45,20,10,12][i]} for i in range(7)
    ]}
    dummy_risks = [
        {"date":dates[i],"max_severity":[4,3,2,2,1,1,2][i],
         "risks":[{"type":["heatwave","heat_stress","rain_risk","rain_risk","none","none","heat_stress"][i]}] if [4,3,2,2,1,1,2][i]>0 else []
        } for i in range(7)
    ]
    dummy_irr = {"schedule":[
        {"date":dates[i],"decision":["IRRIGATE","IRRIGATE","SKIP","SKIP","IRRIGATE","IRRIGATE","REDUCE"][i],
         "volume_liters":[450,420,0,0,380,380,200][i],
         "reason":["Hot day irrigate 5-7AM","High temperature","Rain expected","Rain expected","Normal irrigation","Normal irrigation","Reduce heat"][i]
        } for i in range(7)
    ]}
    dummy_lstm={"rainfall_mm_24h":2.5,"rainfall_mm_48h":8.0,"rainfall_mm_72h":15.0,
                "probability_24h":0.15,"probability_48h":0.35,"probability_72h":0.55}
    dummy_adv="""गेहूं की फसल को सुबह 5-7 बजे सिंचाई करें।
दोपहर में सिंचाई बिल्कुल न करें - पत्तियां जल सकती हैं।
तापमान 42 डिग्री से ऊपर है - फसल पर नजर रखें।
अगले 3 दिन बारिश की संभावना - सिंचाई बंद रखें।
अगले सप्ताह हवा तेज रहेगी - कीटनाशक न छिड़कें।
मिट्टी की नमी जांचते रहें।"""

    pdf = generate_pdf(dummy_farmer, dummy_weather, dummy_risks, dummy_irr, dummy_lstm, dummy_adv, "hi")
    with open("test_report.pdf","wb") as f:
        f.write(pdf)
    print(f"PDF saved: test_report.pdf ({len(pdf)//1024} KB)")
    print("Open test_report.pdf to check!")