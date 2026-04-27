"""
MODULE — NASA POWER API
Fetches 10+ years of historical weather data for LSTM training.
Free API, no key needed.
"""

import requests
import pandas as pd
import json
import os
import sys
sys.path.insert(0, '.')

from utils.logger import get_logger

logger = get_logger("nasa_power")

# ── Cache directory ───────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "nasa_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ── NASA POWER API config ─────────────────────────────────────
NASA_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Parameters we need for LSTM
# PRECTOTCORR = Precipitation (mm/day)
# T2M         = Temperature at 2m (°C)
# RH2M        = Relative Humidity at 2m (%)
# WS2M        = Wind Speed at 2m (m/s)
# PS          = Surface Pressure (kPa)
NASA_PARAMS = "PRECTOTCORR,T2M,RH2M,WS2M,PS"

# ── Indian districts for training data ───────────────────────
TRAINING_DISTRICTS = {
    "indore":        {"lat": 22.719, "lon": 75.857, "state": "Madhya Pradesh"},
    "mumbai":        {"lat": 19.076, "lon": 72.877, "state": "Maharashtra"},
    "delhi":         {"lat": 28.613, "lon": 77.209, "state": "Delhi"},
    "bangalore":     {"lat": 12.971, "lon": 77.594, "state": "Karnataka"},
    "chennai":       {"lat": 13.082, "lon": 80.270, "state": "Tamil Nadu"},
    "kolkata":       {"lat": 22.572, "lon": 88.363, "state": "West Bengal"},
    "hyderabad":     {"lat": 17.385, "lon": 78.486, "state": "Telangana"},
    "pune":          {"lat": 18.520, "lon": 73.856, "state": "Maharashtra"},
    "ahmedabad":     {"lat": 23.022, "lon": 72.571, "state": "Gujarat"},
    "jaipur":        {"lat": 26.912, "lon": 75.787, "state": "Rajasthan"},
    "lucknow":       {"lat": 26.846, "lon": 80.946, "state": "Uttar Pradesh"},
    "patna":         {"lat": 25.594, "lon": 85.137, "state": "Bihar"},
    "bhopal":        {"lat": 23.259, "lon": 77.412, "state": "Madhya Pradesh"},
    "nagpur":        {"lat": 21.145, "lon": 79.088, "state": "Maharashtra"},
    "chandigarh":    {"lat": 30.733, "lon": 76.779, "state": "Punjab"},
    "amritsar":      {"lat": 31.634, "lon": 74.872, "state": "Punjab"},
    "varanasi":      {"lat": 25.317, "lon": 82.973, "state": "Uttar Pradesh"},
    "surat":         {"lat": 21.170, "lon": 72.831, "state": "Gujarat"},
    "visakhapatnam": {"lat": 17.686, "lon": 83.218, "state": "Andhra Pradesh"},
    "coimbatore":    {"lat": 11.016, "lon": 76.955, "state": "Tamil Nadu"},
}


def fetch_nasa_power(lat: float, lon: float, start_year: int = 2014, end_year: int = 2024) -> pd.DataFrame:
    """
    Fetch historical daily weather data from NASA POWER API.
    Returns DataFrame with columns: date, rainfall_mm, temp_c, humidity_pct, wind_ms, pressure_kpa
    Uses local cache to avoid repeated API calls.
    """
    cache_key = f"{lat:.3f}_{lon:.3f}_{start_year}_{end_year}"
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

    # Return cached data if exists
    if os.path.exists(cache_file):
        logger.info(f"Loading cached NASA POWER data: {cache_key}")
        with open(cache_file, "r") as f:
            raw = json.load(f)
        return _parse_nasa_response(raw)

    logger.info(f"Fetching NASA POWER data: lat={lat}, lon={lon}, {start_year}-{end_year}")

    params = {
        "parameters": NASA_PARAMS,
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": f"{start_year}0101",
        "end": f"{end_year}1231",
        "format": "JSON",
    }

    try:
        response = requests.get(NASA_BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        raw = response.json()

        # Cache the response
        with open(cache_file, "w") as f:
            json.dump(raw, f)

        logger.info(f"NASA POWER data fetched and cached: {cache_key}")
        return _parse_nasa_response(raw)

    except requests.exceptions.Timeout:
        logger.error("NASA POWER API timeout")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        logger.error(f"NASA POWER API error: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error fetching NASA POWER data: {e}")
        return pd.DataFrame()


def _parse_nasa_response(raw: dict) -> pd.DataFrame:
    """Parse NASA POWER JSON response into clean DataFrame."""
    try:
        properties = raw.get("properties", {})
        parameter_data = properties.get("parameter", {})

        rainfall   = parameter_data.get("PRECTOTCORR", {})
        temp       = parameter_data.get("T2M", {})
        humidity   = parameter_data.get("RH2M", {})
        wind       = parameter_data.get("WS2M", {})
        pressure   = parameter_data.get("PS", {})

        if not rainfall:
            logger.error("No rainfall data in NASA POWER response")
            return pd.DataFrame()

        dates = sorted(rainfall.keys())
        records = []

        for date_str in dates:
            # Skip annual summary entries (YYYYDDD format with DDD=999)
            if date_str.endswith("13"):
                continue

            try:
                date = pd.to_datetime(date_str, format="%Y%m%d")
            except Exception:
                continue

            rain_val  = rainfall.get(date_str, -999)
            temp_val  = temp.get(date_str, -999)
            hum_val   = humidity.get(date_str, -999)
            wind_val  = wind.get(date_str, -999)
            pres_val  = pressure.get(date_str, -999)

            # NASA uses -999 for missing data
            if any(v == -999 for v in [rain_val, temp_val, hum_val, wind_val, pres_val]):
                continue

            records.append({
                "date":         date,
                "rainfall_mm":  max(0, float(rain_val)),
                "temp_c":       float(temp_val),
                "humidity_pct": float(hum_val),
                "wind_ms":      float(wind_val),
                "pressure_kpa": float(pres_val),
            })

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values("date").reset_index(drop=True)
            logger.info(f"Parsed {len(df)} days of NASA POWER data")

        return df

    except Exception as e:
        logger.error(f"Error parsing NASA POWER response: {e}")
        return pd.DataFrame()


def fetch_all_districts(start_year: int = 2014, end_year: int = 2024) -> dict:
    """
    Fetch historical data for all training districts.
    Returns dict: {district_name: DataFrame}
    Used by model_trainer.py to build LSTM training dataset.
    """
    all_data = {}

    for district, info in TRAINING_DISTRICTS.items():
        logger.info(f"Fetching data for {district}...")
        df = fetch_nasa_power(info["lat"], info["lon"], start_year, end_year)

        if not df.empty:
            df["district"] = district
            df["state"]    = info["state"]
            all_data[district] = df
            logger.info(f"  {district}: {len(df)} days")
        else:
            logger.warning(f"  {district}: No data fetched")

    logger.info(f"Fetched data for {len(all_data)}/{len(TRAINING_DISTRICTS)} districts")
    return all_data


def get_recent_history(lat: float, lon: float, days: int = 30) -> pd.DataFrame:
    """
    Get last N days of historical data for a location.
    Used at inference time to feed LSTM with recent weather sequence.
    """
    df = fetch_nasa_power(lat, lon, start_year=2020, end_year=2024)

    if df.empty:
        return df

    df = df.sort_values("date").tail(days).reset_index(drop=True)
    return df


def get_7day_sequence(lat: float, lon: float) -> list:
    """
    Get last 7 days of weather as list of dicts.
    This is the direct input format for LSTM prediction.
    Returns: [{"temp": x, "humidity": x, "pressure": x, "rainfall": x, "wind": x}, ...]
    """
    df = get_recent_history(lat, lon, days=7)

    if df.empty or len(df) < 7:
        logger.warning(f"Not enough historical data for ({lat}, {lon}), using defaults")
        return [{"temp": 28.0, "humidity": 65.0, "pressure": 101.3, "rainfall": 0.0, "wind": 2.5}] * 7

    sequence = []
    for _, row in df.iterrows():
        sequence.append({
            "temp":     row["temp_c"],
            "humidity": row["humidity_pct"],
            "pressure": row["pressure_kpa"],
            "rainfall": row["rainfall_mm"],
            "wind":     row["wind_ms"],
        })

    return sequence


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing NASA POWER fetch for Indore...")
    df = fetch_nasa_power(22.719, 75.857, start_year=2022, end_year=2023)

    if not df.empty:
        print(f"Fetched {len(df)} days")
        print(df.head(10).to_string())
        print(f"\nRainfall stats:")
        print(f"  Mean: {df['rainfall_mm'].mean():.2f} mm/day")
        print(f"  Max:  {df['rainfall_mm'].max():.2f} mm")
        print(f"  Rainy days (>1mm): {(df['rainfall_mm'] > 1).sum()}")
    else:
        print("No data fetched!")