"""
MODULE 2 — Smart Irrigation Brain
ET₀ calculation using Penman-Monteith (simplified FAO-56 method)
Outputs: IRRIGATE / SKIP / REDUCE with volume estimate
"""

import math
from utils.crop_profiles import get_crop_profile
from utils.logger import get_logger

logger = get_logger("irrigation_model")

# Crop coefficient (Kc) by growth stage — FAO-56 standard values
CROP_KC = {
    "wheat":     {"sowing": 0.3, "germination": 0.4, "tillering": 0.7, "flowering": 1.15, "grain_filling": 0.9, "harvest": 0.4},
    "rice":      {"nursery": 1.05, "transplanting": 1.05, "vegetative": 1.1, "flowering": 1.2, "grain_filling": 1.0, "harvest": 0.75},
    "soybean":   {"sowing": 0.35, "vegetative": 0.7, "flowering": 1.1, "pod_fill": 1.1, "maturity": 0.75, "harvest": 0.45},
    "cotton":    {"sowing": 0.35, "seedling": 0.5, "squaring": 0.8, "flowering": 1.15, "boll_development": 1.1, "harvest": 0.6},
    "sugarcane": {"germination": 0.4, "tillering": 0.7, "grand_growth": 1.25, "ripening": 0.75, "harvest": 0.5},
    "onion":     {"sowing": 0.5, "seedling": 0.6, "vegetative": 0.75, "bulb_development": 1.05, "maturity": 0.85, "harvest": 0.75},
    "tomato":    {"nursery": 0.45, "transplanting": 0.6, "vegetative": 0.9, "flowering": 1.1, "fruiting": 1.15, "harvest": 0.8},
}


def calculate_et0(temp_c: float, humidity_pct: float, wind_kmh: float, solar_radiation: float = None) -> float:
    """
    Simplified Penman-Monteith ET₀ calculation (FAO-56).
    Returns mm/day water evapotranspiration.
    solar_radiation: MJ/m²/day (estimated from temp if not provided)
    """
    # Estimate solar radiation if not provided (rough estimate from temp range)
    if solar_radiation is None:
        solar_radiation = max(5.0, temp_c * 0.6)

    wind_ms = wind_kmh / 3.6  # convert to m/s

    # Saturation vapour pressure
    e_s = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))

    # Actual vapour pressure
    e_a = e_s * (humidity_pct / 100)

    # Slope of saturation vapour pressure curve
    delta = 4098 * e_s / ((temp_c + 237.3) ** 2)

    # Psychrometric constant (approx at 1 atm)
    gamma = 0.0665

    # Net radiation (simplified)
    rn = solar_radiation * 0.77 - 4.5  # accounting for albedo and longwave

    # ET₀ formula (simplified Penman-Monteith)
    numerator = (0.408 * delta * rn) + (gamma * (900 / (temp_c + 273)) * wind_ms * (e_s - e_a))
    denominator = delta + gamma * (1 + 0.34 * wind_ms)

    et0 = numerator / denominator
    return max(0.0, round(et0, 2))


def get_irrigation_schedule(
    crop: str,
    growth_stage: str,
    field_area_acres: float,
    daily_forecast: list,
    soil_type: str = "loamy"
) -> dict:
    """
    Generate 7-day irrigation schedule.
    Returns daily IRRIGATE / SKIP / REDUCE commands with volume.
    """
    profile = get_crop_profile(crop)
    kc_table = CROP_KC.get(crop, {})
    kc = kc_table.get(growth_stage, 0.8)

    # Soil water holding capacity factor
    soil_factor = {"sandy": 0.7, "loamy": 1.0, "clay": 1.2, "black-cotton": 1.15}.get(soil_type, 1.0)

    # Convert acres to hectares
    area_ha = field_area_acres * 0.4047

    schedule = []

    for day in daily_forecast:
        temp = day.get("temp_max_c") or 25.0
        humidity = 60.0
        wind = day.get("wind_max_kmh") or 10.0
        rainfall = day.get("rainfall_mm") or 0.0
        rain_prob = day.get("rainfall_prob_pct") or 0

        et0 = calculate_et0(temp, humidity, wind)
        etc = et0 * kc  # Crop evapotranspiration

        # Net irrigation requirement (subtract rainfall)
        net_irrigation_mm = max(0, etc - rainfall)

        # Decision logic
        if rain_prob >= 70 or rainfall >= etc * 1.2:
            decision = "SKIP"
            reason = f"Rain expected ({rain_prob}% probability, {rainfall}mm). Natural watering sufficient."
            volume_liters = 0
        elif net_irrigation_mm < 1.5:
            decision = "REDUCE"
            reason = f"Partial rainfall ({rainfall}mm). Light irrigation needed."
            # Apply drip irrigation wetted area fraction (0.1) and efficiency factor (0.7)
            volume_liters = round((net_irrigation_mm * soil_factor * area_ha * 10000 * 0.1) / 0.7, 0)
        else:
            decision = "IRRIGATE"
            reason = f"Water needed: {etc:.1f}mm | Expected Rain: {rainfall}mm. Full irrigation required."
            volume_liters = round((net_irrigation_mm * soil_factor * area_ha * 10000 * 0.1) / 0.7, 0)

        schedule.append({
            "date": day.get("date"),
            "decision": decision,
            "reason": reason,
            "et0_mm": et0,
            "crop_water_need_mm": round(etc, 2),
            "expected_rainfall_mm": rainfall,
            "net_irrigation_mm": round(net_irrigation_mm, 2),
            "volume_liters": int(volume_liters),
            "volume_liters_display": f"{int(volume_liters):,} L"
        })

    irrigate_days = sum(1 for d in schedule if d["decision"] == "IRRIGATE")
    total_volume = sum(d["volume_liters"] for d in schedule)

    logger.info(f"Irrigation schedule: {crop} | {irrigate_days}/7 days irrigation needed")

    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "field_area_acres": field_area_acres,
        "soil_type": soil_type,
        "kc_used": kc,
        "schedule": schedule,
        "summary": {
            "irrigate_days": irrigate_days,
            "skip_days": sum(1 for d in schedule if d["decision"] == "SKIP"),
            "reduce_days": sum(1 for d in schedule if d["decision"] == "REDUCE"),
            "total_volume_liters": int(total_volume),
            "total_volume_display": f"{int(total_volume):,} L over 7 days"
        }
    }
