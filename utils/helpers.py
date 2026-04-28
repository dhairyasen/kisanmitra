"""
MODULE — Helper Utilities
Shared utility functions used across KisanMitra modules.
"""

import sys
sys.path.insert(0, '.')

import math
import re
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("helpers")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates in kilometers.
    Used to find nearest district for a given farmer location.
    """
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_season(lat: float, month: int) -> str:
    """
    Detect Indian agricultural season based on location and month.
    Returns: 'kharif', 'rabi', or 'zaid'
    """
    if month in [6, 7, 8, 9, 10]:
        return "kharif"   # June-October: monsoon crops
    elif month in [11, 12, 1, 2, 3]:
        return "rabi"     # Nov-March: winter crops
    else:
        return "zaid"     # April-June: summer crops


def validate_indian_coordinates(lat: float, lon: float) -> bool:
    """Check if coordinates are within India bounds."""
    return 8.0 <= lat <= 37.0 and 68.0 <= lon <= 97.0


def format_phone(phone: str) -> str:
    """
    Normalize Indian phone numbers to +91XXXXXXXXXX format.
    Accepts: 9876543210, 09876543210, +919876543210
    """
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) == 11 and digits.startswith('0'):
        return f"+91{digits[1:]}"
    elif len(digits) == 12 and digits.startswith('91'):
        return f"+{digits}"
    return phone  # return as-is if unrecognized


def get_time_greeting(language: str = "hi") -> str:
    """Return time-appropriate greeting in farmer's language."""
    hour = datetime.now().hour

    greetings = {
        "hi": {
            "morning":   "सुप्रभात",
            "afternoon": "नमस्ते",
            "evening":   "शुभ संध्या",
        },
        "mr": {
            "morning":   "सुप्रभात",
            "afternoon": "नमस्कार",
            "evening":   "शुभ संध्याकाळ",
        },
        "kn": {
            "morning":   "ಶುಭೋದಯ",
            "afternoon": "ನಮಸ್ಕಾರ",
            "evening":   "ಶುಭ ಸಂಜೆ",
        },
        "te": {
            "morning":   "శుభోదయం",
            "afternoon": "నమస్కారం",
            "evening":   "శుభ సాయంత్రం",
        },
        "ta": {
            "morning":   "காலை வணக்கம்",
            "afternoon": "வணக்கம்",
            "evening":   "மாலை வணக்கம்",
        },
        "pa": {
            "morning":   "ਸ਼ੁਭ ਸਵੇਰ",
            "afternoon": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ",
            "evening":   "ਸ਼ੁਭ ਸ਼ਾਮ",
        },
        "bn": {
            "morning":   "শুভ সকাল",
            "afternoon": "নমস্কার",
            "evening":   "শুভ সন্ধ্যা",
        },
        "gu": {
            "morning":   "સુપ્રભાત",
            "afternoon": "નમસ્તે",
            "evening":   "શુભ સાંજ",
        },
        "en": {
            "morning":   "Good morning",
            "afternoon": "Good afternoon",
            "evening":   "Good evening",
        },
    }

    if hour < 12:
        period = "morning"
    elif hour < 17:
        period = "afternoon"
    else:
        period = "evening"

    lang_greetings = greetings.get(language, greetings["hi"])
    return lang_greetings.get(period, "नमस्ते")


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return round(mm / 25.4, 2)


def celsius_to_fahrenheit(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return round((c * 9/5) + 32, 1)


def kmh_to_ms(kmh: float) -> float:
    """Convert km/h to m/s."""
    return round(kmh / 3.6, 2)


def get_risk_color(severity: int) -> str:
    """Return color code for severity level."""
    colors = {0: "green", 1: "green", 2: "yellow", 3: "orange", 4: "red", 5: "darkred"}
    return colors.get(severity, "gray")


def get_risk_emoji(severity: int) -> str:
    """Return emoji for severity level."""
    emojis = {0: "✅", 1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "🚨"}
    return emojis.get(severity, "⚪")


def truncate_text(text: str, max_chars: int = 160) -> str:
    """
    Truncate text to max characters (SMS limit = 160).
    Adds '...' if truncated.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


def find_nearest_district(lat: float, lon: float, districts: dict) -> str:
    """
    Find nearest district from a dict of {name: {lat, lon}}.
    Returns district name.
    """
    nearest = None
    min_dist = float("inf")

    for name, coords in districts.items():
        dist = haversine_distance(lat, lon, coords["lat"], coords["lon"])
        if dist < min_dist:
            min_dist = dist
            nearest = name

    return nearest


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing helpers...")
    print(f"Distance Indore-Mumbai: {haversine_distance(22.719, 75.857, 19.076, 72.877):.1f} km")
    print(f"Season (July, Indore): {get_season(22.719, 7)}")
    print(f"Valid India coords: {validate_indian_coordinates(22.719, 75.857)}")
    print(f"Format phone: {format_phone('9876543210')}")
    print(f"Greeting (hi): {get_time_greeting('hi')}")
    print(f"Risk emoji (4): {get_risk_emoji(4)}")
    print(f"Truncate: {truncate_text('Hello world ' * 20, 160)}")
    print("Helpers working!")