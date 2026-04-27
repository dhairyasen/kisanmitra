"""
MODULE — Data Normalizer
Converts NASA POWER and Open-Meteo responses into unified schema for LSTM.
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger("data_normalizer")


def normalize_nasa_power(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize NASA POWER DataFrame into unified schema.
    Input columns:  date, rainfall_mm, temp_c, humidity_pct, wind_ms, pressure_kpa
    Output columns: date, rainfall_mm, temp_c, humidity_pct, wind_ms, pressure_kpa
    (same — just validates and cleans)
    """
    if df.empty:
        return df

    required = ["date", "rainfall_mm", "temp_c", "humidity_pct", "wind_ms", "pressure_kpa"]
    for col in required:
        if col not in df.columns:
            logger.error(f"Missing column in NASA data: {col}")
            return pd.DataFrame()

    df = df.copy()

    # Clip to realistic ranges
    df["rainfall_mm"]  = df["rainfall_mm"].clip(0, 500)
    df["temp_c"]       = df["temp_c"].clip(-20, 55)
    df["humidity_pct"] = df["humidity_pct"].clip(0, 100)
    df["wind_ms"]      = df["wind_ms"].clip(0, 50)
    df["pressure_kpa"] = df["pressure_kpa"].clip(80, 110)

    # Fill any remaining NaNs with column median
    for col in required[1:]:
        df[col] = df[col].fillna(df[col].median())

    df = df.sort_values("date").reset_index(drop=True)
    return df[required]


def normalize_openmeteo(raw: dict, lat: float, lon: float) -> pd.DataFrame:
    """
    Normalize Open-Meteo API response into unified schema.
    Used to get recent weather for LSTM inference.
    """
    try:
        daily = raw.get("daily", {})
        dates       = daily.get("time", [])
        rain        = daily.get("precipitation_sum", [])
        temp_max    = daily.get("temperature_2m_max", [])
        temp_min    = daily.get("temperature_2m_min", [])
        humidity    = daily.get("relative_humidity_2m_mean", daily.get("precipitation_probability_mean", []))
        wind        = daily.get("wind_speed_10m_max", [])
        pressure    = daily.get("surface_pressure_mean", [])

        if not dates:
            logger.error("No dates in Open-Meteo response")
            return pd.DataFrame()

        records = []
        for i, date_str in enumerate(dates):
            temp_max_val = temp_max[i] if i < len(temp_max) and temp_max[i] is not None else 28.0
            temp_min_val = temp_min[i] if i < len(temp_min) and temp_min[i] is not None else 20.0
            temp_avg = (temp_max_val + temp_min_val) / 2

            records.append({
                "date":         pd.to_datetime(date_str),
                "rainfall_mm":  max(0, rain[i]) if i < len(rain) and rain[i] is not None else 0.0,
                "temp_c":       temp_avg,
                "humidity_pct": humidity[i] if i < len(humidity) and humidity[i] is not None else 65.0,
                "wind_ms":      (wind[i] / 3.6) if i < len(wind) and wind[i] is not None else 2.5,
                "pressure_kpa": (pressure[i] / 10) if i < len(pressure) and pressure[i] is not None else 101.3,
            })

        df = pd.DataFrame(records)
        return normalize_nasa_power(df)

    except Exception as e:
        logger.error(f"Error normalizing Open-Meteo data: {e}")
        return pd.DataFrame()


def sequence_to_array(sequence: list) -> np.ndarray:
    """
    Convert a list of weather dicts to numpy array for LSTM input.
    Input:  [{"temp": x, "humidity": x, "pressure": x, "rainfall": x, "wind": x}, ...]
    Output: np.array shape (7, 5) — 7 days, 5 features
    Feature order: [temp_c, humidity_pct, pressure_kpa, rainfall_mm, wind_ms]
    """
    FEATURE_ORDER = ["temp", "humidity", "pressure", "rainfall", "wind"]

    arr = []
    for day in sequence:
        row = [
            float(day.get("temp",     28.0)),
            float(day.get("humidity", 65.0)),
            float(day.get("pressure", 101.3)),
            float(day.get("rainfall", 0.0)),
            float(day.get("wind",     2.5)),
        ]
        arr.append(row)

    return np.array(arr, dtype=np.float32)


def df_to_sequences(df: pd.DataFrame, window: int = 7) -> tuple:
    """
    Convert historical DataFrame into (X, y) sequences for LSTM training.
    X shape: (n_samples, window, 5)  — input sequences
    y shape: (n_samples, 1)          — next day rainfall
    """
    FEATURES = ["temp_c", "humidity_pct", "pressure_kpa", "rainfall_mm", "wind_ms"]

    if df.empty or len(df) < window + 1:
        logger.error(f"Not enough data for sequences: {len(df)} rows, need {window + 1}")
        return np.array([]), np.array([])

    values = df[FEATURES].values.astype(np.float32)
    X, y = [], []

    for i in range(len(values) - window):
        X.append(values[i:i + window])
        y.append(values[i + window][3])  # index 3 = rainfall_mm

    X = np.array(X)
    y = np.array(y).reshape(-1, 1)

    logger.info(f"Created {len(X)} sequences from {len(df)} days")
    return X, y


def scale_features(X_train: np.ndarray, X_test: np.ndarray = None):
    """
    Min-max scale features to [0, 1] range for LSTM.
    Returns: (X_train_scaled, X_test_scaled, min_vals, max_vals)
    """
    min_vals = X_train.min(axis=(0, 1), keepdims=True)
    max_vals = X_train.max(axis=(0, 1), keepdims=True)
    range_vals = np.where(max_vals - min_vals == 0, 1, max_vals - min_vals)

    X_train_scaled = (X_train - min_vals) / range_vals

    if X_test is not None:
        X_test_scaled = (X_test - min_vals) / range_vals
        return X_train_scaled, X_test_scaled, min_vals, max_vals

    return X_train_scaled, min_vals, max_vals


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    from ingestion.nasa_power import fetch_nasa_power

    print("Testing data normalizer...")
    df = fetch_nasa_power(22.719, 75.857, start_year=2022, end_year=2023)
    df_clean = normalize_nasa_power(df)

    print(f"Normalized: {len(df_clean)} rows")
    print(df_clean.head(5).to_string())

    X, y = df_to_sequences(df_clean, window=7)
    print(f"\nSequences: X={X.shape}, y={y.shape}")

    X_scaled, min_v, max_v = scale_features(X)
    print(f"Scaled X range: {X_scaled.min():.2f} to {X_scaled.max():.2f}")
    print("\nData normalizer working!")