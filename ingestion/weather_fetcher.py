"""
MODULE 1 — Weather Data Ingestion
Fetches from Open-Meteo (primary) + NASA POWER (secondary)
No API key required for both — fully free.
"""

import requests
import time
from datetime import datetime, timedelta
from typing import Optional
from utils.logger import get_logger

logger = get_logger("weather_fetcher")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

def fetch_open_meteo(lat: float, lon: float, days: int = 7) -> Optional[dict]:
    """
    Fetch hyperlocal forecast from Open-Meteo API.
    Returns normalized weather data for next `days` days.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relativehumidity_2m",
            "precipitation_probability",
            "precipitation",
            "windspeed_10m",
            "surface_pressure",
            "weathercode"
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max",
            "precipitation_probability_max"
        ],
        "forecast_days": days,
        "timezone": "Asia/Kolkata",
        "windspeed_unit": "kmh"
    }

    for attempt in range(3):  # retry up to 3 times
        try:
            response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Open-Meteo fetch success for ({lat}, {lon})")
            return _normalize_open_meteo(data, lat, lon)
        except requests.exceptions.RequestException as e:
            logger.error(f"Open-Meteo attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)  # exponential backoff

    logger.error(f"Open-Meteo failed after 3 attempts for ({lat}, {lon})")
    return None


def _normalize_open_meteo(raw: dict, lat: float, lon: float) -> dict:
    """Convert Open-Meteo response to our standard schema."""
    daily = raw.get("daily", {})
    hourly = raw.get("hourly", {})

    normalized_days = []
    times = daily.get("time", [])

    for i, date_str in enumerate(times):
        normalized_days.append({
            "date": date_str,
            "lat": lat,
            "lon": lon,
            "temp_max_c": daily.get("temperature_2m_max", [None])[i],
            "temp_min_c": daily.get("temperature_2m_min", [None])[i],
            "rainfall_mm": daily.get("precipitation_sum", [None])[i],
            "wind_max_kmh": daily.get("windspeed_10m_max", [None])[i],
            "rainfall_prob_pct": daily.get("precipitation_probability_max", [None])[i],
            "source": "open-meteo"
        })

    # Also extract hourly for the first 24 hours (for alert detection)
    hourly_data = []
    for i in range(min(24, len(hourly.get("time", [])))):
        hourly_data.append({
            "timestamp": hourly.get("time", [])[i],
            "temp_c": hourly.get("temperature_2m", [None])[i],
            "humidity_pct": hourly.get("relativehumidity_2m", [None])[i],
            "rainfall_prob_pct": hourly.get("precipitation_probability", [None])[i],
            "rainfall_mm": hourly.get("precipitation", [None])[i],
            "wind_kmh": hourly.get("windspeed_10m", [None])[i],
            "pressure_hpa": hourly.get("surface_pressure", [None])[i],
        })

    return {
        "location": {"lat": lat, "lon": lon},
        "fetched_at": datetime.now().isoformat(),
        "daily_forecast": normalized_days,
        "hourly_next24h": hourly_data,
        "source": "open-meteo"
    }


def fetch_nasa_power(lat: float, lon: float) -> Optional[dict]:
    """
    Fetch historical climate data from NASA POWER API.
    Used to supplement Open-Meteo with longer-term context.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    params = {
        "parameters": "T2M,PRECTOTCORR,WS10M,RH2M,PS",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON"
    }

    for attempt in range(3):
        try:
            response = requests.get(NASA_POWER_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"NASA POWER fetch success for ({lat}, {lon})")
            return _normalize_nasa(data, lat, lon)
        except requests.exceptions.RequestException as e:
            logger.error(f"NASA POWER attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)

    logger.error(f"NASA POWER failed after 3 attempts for ({lat}, {lon})")
    return None


def _normalize_nasa(raw: dict, lat: float, lon: float) -> dict:
    """Convert NASA POWER response to standard schema."""
    try:
        props = raw["properties"]["parameter"]
        dates = list(props.get("T2M", {}).keys())

        history = []
        for date_str in dates:
            history.append({
                "date": date_str,
                "lat": lat,
                "lon": lon,
                "temp_c": props.get("T2M", {}).get(date_str),
                "rainfall_mm": props.get("PRECTOTCORR", {}).get(date_str),
                "wind_kmh": props.get("WS10M", {}).get(date_str),
                "humidity_pct": props.get("RH2M", {}).get(date_str),
                "pressure_hpa": props.get("PS", {}).get(date_str),
                "source": "nasa-power"
            })

        return {
            "location": {"lat": lat, "lon": lon},
            "fetched_at": datetime.now().isoformat(),
            "historical_30days": history,
            "source": "nasa-power"
        }
    except (KeyError, TypeError) as e:
        logger.error(f"NASA POWER normalization error: {e}")
        return None


def get_full_weather_context(lat: float, lon: float) -> dict:
    """
    Master function: fetches from all sources and combines.
    This is what the rest of the system calls.
    """
    logger.info(f"Fetching full weather context for ({lat}, {lon})")

    forecast = fetch_open_meteo(lat, lon, days=7)
    history = fetch_nasa_power(lat, lon)

    return {
        "forecast": forecast,
        "history": history,
        "status": "ok" if forecast else "degraded"
    }
