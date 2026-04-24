"""
LangChain Tools — functions the AI agent can call.
Each tool wraps a core module function.
"""

import sys
sys.path.insert(0, '.')

import json
from langchain.tools import tool
from ingestion.weather_fetcher import fetch_open_meteo
from models.risk_classifier import batch_classify
from models.irrigation_model import get_irrigation_schedule
from utils.crop_profiles import get_crop_profile, SUPPORTED_CROPS
from utils.logger import get_logger

logger = get_logger("agent_tools")


@tool
def get_weather_forecast(input: str) -> str:
    """
    Get 7-day weather forecast for a location.
    Input format: "lat,lon" e.g. "19.076,72.877"
    Returns temperature, rainfall, wind data.
    """
    try:
        parts = input.strip().split(",")
        lat, lon = float(parts[0]), float(parts[1])
        data = fetch_open_meteo(lat, lon, days=7)
        if not data:
            return "Weather data unavailable right now."
        days = data["daily_forecast"][:3]  # next 3 days summary
        summary = []
        for d in days:
            summary.append(
                f"{d['date']}: Max {d['temp_max_c']}°C, "
                f"Rain {d['rainfall_mm']}mm ({d['rainfall_prob_pct']}% chance), "
                f"Wind {d['wind_max_kmh']}km/h"
            )
        return "\n".join(summary)
    except Exception as e:
        logger.error(f"get_weather_forecast tool error: {e}")
        return f"Could not fetch weather: {str(e)}"


@tool
def get_crop_risk(input: str) -> str:
    """
    Get weather risk assessment for a crop.
    Input format: "crop,growth_stage,lat,lon"
    e.g. "wheat,flowering,28.6,77.2"
    Returns detected risks and advisories.
    """
    try:
        parts = input.strip().split(",")
        crop = parts[0].strip()
        stage = parts[1].strip()
        lat = float(parts[2])
        lon = float(parts[3])

        weather = fetch_open_meteo(lat, lon, days=3)
        if not weather:
            return "Cannot assess risk — weather data unavailable."

        results = batch_classify(crop, stage, weather["daily_forecast"][:3])

        output = []
        for r in results:
            if r.get("risks"):
                for risk in r["risks"]:
                    output.append(
                        f"{r['date']}: {risk['type'].upper()} risk "
                        f"(Severity: {risk['severity_label']}) — {risk['advisory']}"
                    )
            else:
                output.append(f"{r['date']}: No risks detected. Conditions are safe.")

        return "\n".join(output) if output else "No risks detected for next 3 days."
    except Exception as e:
        logger.error(f"get_crop_risk tool error: {e}")
        return f"Risk assessment failed: {str(e)}"


@tool
def get_irrigation_advice(input: str) -> str:
    """
    Get irrigation schedule for a crop.
    Input format: "crop,growth_stage,lat,lon,area_acres,soil_type"
    e.g. "wheat,flowering,28.6,77.2,2.5,loamy"
    Returns IRRIGATE/SKIP/REDUCE for next 7 days.
    """
    try:
        parts = input.strip().split(",")
        crop = parts[0].strip()
        stage = parts[1].strip()
        lat = float(parts[2])
        lon = float(parts[3])
        area = float(parts[4]) if len(parts) > 4 else 1.0
        soil = parts[5].strip() if len(parts) > 5 else "loamy"

        weather = fetch_open_meteo(lat, lon, days=7)
        if not weather:
            return "Cannot generate schedule — weather data unavailable."

        schedule = get_irrigation_schedule(crop, stage, area, weather["daily_forecast"], soil)
        output = [f"7-Day Irrigation Schedule for {crop} ({area} acres):"]
        for day in schedule["schedule"]:
            output.append(f"  {day['date']}: {day['decision']} — {day['reason']}")

        summary = schedule["summary"]
        output.append(f"\nTotal: {summary['irrigate_days']} irrigation days, "
                      f"{summary['total_volume_display']}")
        return "\n".join(output)
    except Exception as e:
        logger.error(f"get_irrigation_advice tool error: {e}")
        return f"Irrigation schedule failed: {str(e)}"


@tool
def get_crop_info(crop_name: str) -> str:
    """
    Get information about a supported crop.
    Input: crop name e.g. "wheat", "rice", "onion"
    Returns crop profile with risk thresholds.
    """
    try:
        profile = get_crop_profile(crop_name.strip().lower())
        return (
            f"Crop: {crop_name} ({profile['name_hi']})\n"
            f"Season: {profile['season']}\n"
            f"Frost risk below: {profile['frost_risk_temp_c']}°C\n"
            f"Heatwave above: {profile['heatwave_temp_c']}°C\n"
            f"Max safe rain: {profile['max_rain_mm_day']}mm/day\n"
            f"Wind risk above: {profile['wind_risk_kmh']}km/h\n"
            f"Growth stages: {', '.join(profile['growth_stages'])}"
        )
    except ValueError:
        return f"'{crop_name}' not supported. Supported crops: {', '.join(SUPPORTED_CROPS)}"


ALL_TOOLS = [get_weather_forecast, get_crop_risk, get_irrigation_advice, get_crop_info]
