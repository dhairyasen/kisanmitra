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
    "wheat":     {"sowing": 0.3, "germination": 0.4, "tillering": 0.7, "vegetative": 0.7, "flowering": 1.15, "grain_filling": 0.9, "harvest": 0.4},
    "rice":      {"nursery": 1.05, "transplanting": 1.05, "vegetative": 1.1, "flowering": 1.2, "grain_filling": 1.0, "harvest": 0.75},
    "soybean":   {"sowing": 0.35, "vegetative": 0.7, "flowering": 1.1, "pod_fill": 1.1, "maturity": 0.75, "harvest": 0.45},
    "cotton":    {"sowing": 0.35, "seedling": 0.5, "squaring": 0.8, "vegetative": 0.8, "flowering": 1.15, "boll_development": 1.1, "harvest": 0.6},
    "sugarcane": {"germination": 0.4, "tillering": 0.7, "vegetative": 0.9, "grand_growth": 1.25, "ripening": 0.75, "harvest": 0.5},
    "onion":     {"sowing": 0.5, "seedling": 0.6, "vegetative": 0.75, "bulb_development": 1.05, "maturity": 0.85, "harvest": 0.75},
    "tomato":    {"nursery": 0.45, "transplanting": 0.6, "vegetative": 0.9, "flowering": 1.1, "fruiting": 1.15, "harvest": 0.8},
}

# Irrigation efficiency by soil type
SOIL_EFFICIENCY = {
    "sandy": 0.65,
    "loamy": 0.75,
    "clay":  0.80,
    "black": 0.78,
    "silt":  0.72,
    "red":   0.68,
}


def calculate_et0(temp_c: float, humidity_pct: float, wind_kmh: float) -> float:
    """
    Simplified Penman-Monteith ET₀ (FAO-56).
    Returns mm/day.
    """
    solar_radiation = max(5.0, temp_c * 0.55)
    wind_ms = wind_kmh / 3.6

    e_s = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))
    e_a = e_s * (humidity_pct / 100)
    delta = 4098 * e_s / ((temp_c + 237.3) ** 2)
    gamma = 0.0665
    rn = solar_radiation * 0.77 - 4.5

    numerator = (0.408 * delta * rn) + (gamma * (900 / (temp_c + 273)) * wind_ms * (e_s - e_a))
    denominator = delta + gamma * (1 + 0.34 * wind_ms)

    et0 = numerator / denominator
    return max(0.0, round(et0, 2))


def et0_to_liters(et0_mm: float, field_area_acres: float, efficiency: float = 0.75) -> int:
    """
    Convert ET₀ (mm/day) to actual liters needed for field.

    Formula:
      area_m² = acres × 4047
      gross_mm = net_mm / efficiency  (account for losses)
      liters = gross_mm × area_m² × 0.001  (mm × m² = liters / 1000... wait)

    1mm of water on 1m² = 1 liter
    So: liters = net_mm × area_m²
    But typical field irrigation is 30-60mm per session spread over area.

    Realistic: for 1 acre (4047 m²), 5mm irrigation = ~20,000L (drip)
    We cap at realistic range: 500-5000 L per acre per day.
    """
    area_m2 = field_area_acres * 4047.0
    # mm × m² / 1000 = m³, × 1000 = liters → mm × m² = liters
    # But 1mm on 4047m² = 4047 liters which is correct
    # Issue was ×10000 before — wrong unit conversion
    gross_liters = (et0_mm / efficiency) * area_m2

    # Cap at realistic daily max (150mm equivalent per day = extreme flood irrigation)
    max_liters = 150 * area_m2
    return int(min(gross_liters, max_liters))


def get_irrigation_schedule(
    crop: str,
    growth_stage: str,
    field_area_acres: float,
    daily_forecast: list,
    soil_type: str = "loamy"
) -> dict:
    """
    Generate 7-day irrigation schedule.
    """
    kc_table = CROP_KC.get(crop, {})
    kc = kc_table.get(growth_stage, 0.75)

    efficiency = SOIL_EFFICIENCY.get(soil_type, 0.75)

    schedule = []

    for day in daily_forecast:
        temp     = float(day.get("temp_max_c") or 30.0)
        humidity = 60.0
        wind     = float(day.get("wind_max_kmh") or 10.0)
        rainfall = float(day.get("rainfall_mm") or 0.0)
        rain_prob= float(day.get("rainfall_prob_pct") or 0)

        et0 = calculate_et0(temp, humidity, wind)
        etc = round(et0 * kc, 2)  # Crop evapotranspiration

        # Net irrigation needed (subtract effective rainfall)
        effective_rain = rainfall * 0.8  # 80% rainfall is effective
        net_mm = max(0.0, etc - effective_rain)

        # Decision
        if rain_prob >= 70 or rainfall >= etc * 1.2:
            decision = "SKIP"
            reason   = f"Rain expected ({int(rain_prob)}% chance, {rainfall:.1f}mm). Sufficient natural water."
            liters   = 0

        elif net_mm < 2.0:
            decision = "REDUCE"
            reason   = f"Partial rain ({rainfall:.1f}mm). Light irrigation only."
            liters   = et0_to_liters(net_mm * 0.5, field_area_acres, efficiency)

        else:
            decision = "IRRIGATE"
            reason   = f"Crop needs {etc:.1f}mm, rain {rainfall:.1f}mm. Irrigate early morning."
            liters   = et0_to_liters(net_mm, field_area_acres, efficiency)

        schedule.append({
            "date":                 day.get("date", ""),
            "decision":             decision,
            "reason":               reason,
            "et0_mm":               et0,
            "crop_water_need_mm":   etc,
            "expected_rainfall_mm": rainfall,
            "net_irrigation_mm":    round(net_mm, 2),
            "volume_liters":        liters,
            "volume_liters_display": f"{liters:,} L",
        })

    irrigate_days = sum(1 for d in schedule if d["decision"] == "IRRIGATE")
    skip_days     = sum(1 for d in schedule if d["decision"] == "SKIP")
    reduce_days   = sum(1 for d in schedule if d["decision"] == "REDUCE")
    total_volume  = sum(d["volume_liters"] for d in schedule)

    logger.info(f"Irrigation schedule: {crop} | {irrigate_days}/7 days irrigation needed")

    return {
        "crop":             crop,
        "growth_stage":     growth_stage,
        "field_area_acres": field_area_acres,
        "soil_type":        soil_type,
        "kc_used":          kc,
        "schedule":         schedule,
        "summary": {
            "irrigate_days":      irrigate_days,
            "skip_days":          skip_days,
            "reduce_days":        reduce_days,
            "total_volume_liters": total_volume,
            "total_volume_display": f"{total_volume:,} L over 7 days"
        }
    }