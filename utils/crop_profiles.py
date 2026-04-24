"""
Verified crop risk thresholds based on FAO, ICAR & peer-reviewed research.
All 7 crops supported in Phase 1.
"""

CROP_PROFILES = {
    "wheat": {
        "name_hi": "गेहूं",
        "season": "rabi",
        "frost_risk_temp_c": 2.0,
        "heatwave_temp_c": 35.0,
        "max_rain_mm_day": 40.0,
        "wind_risk_kmh": 60.0,
        "growth_stages": ["sowing", "germination", "tillering", "flowering", "grain_filling", "harvest"],
        "water_requirement_mm": 450,
    },
    "rice": {
        "name_hi": "चावल",
        "season": "kharif",
        "frost_risk_temp_c": 15.0,
        "heatwave_temp_c": 40.0,
        "max_rain_mm_day": 80.0,
        "wind_risk_kmh": 70.0,
        "growth_stages": ["nursery", "transplanting", "vegetative", "flowering", "grain_filling", "harvest"],
        "water_requirement_mm": 1200,
    },
    "soybean": {
        "name_hi": "सोयाबीन",
        "season": "kharif",
        "frost_risk_temp_c": 5.0,
        "heatwave_temp_c": 38.0,
        "max_rain_mm_day": 50.0,
        "wind_risk_kmh": 55.0,
        "growth_stages": ["sowing", "vegetative", "flowering", "pod_fill", "maturity", "harvest"],
        "water_requirement_mm": 500,
    },
    "cotton": {
        "name_hi": "कपास",
        "season": "kharif",
        "frost_risk_temp_c": 10.0,
        "heatwave_temp_c": 42.0,
        "max_rain_mm_day": 60.0,
        "wind_risk_kmh": 65.0,
        "growth_stages": ["sowing", "seedling", "squaring", "flowering", "boll_development", "harvest"],
        "water_requirement_mm": 700,
    },
    "sugarcane": {
        "name_hi": "गन्ना",
        "season": "annual",
        "frost_risk_temp_c": 5.0,
        "heatwave_temp_c": 38.0,       # FAO verified: photosynthesis drops above 38°C
        "max_rain_mm_day": 70.0,
        "wind_risk_kmh": 75.0,
        "growth_stages": ["germination", "tillering", "grand_growth", "ripening", "harvest"],
        "water_requirement_mm": 2000,
    },
    "onion": {
        "name_hi": "प्याज",
        "season": "rabi",
        "frost_risk_temp_c": 3.0,
        "heatwave_temp_c": 35.0,       # ICAR verified: bulb development optimal 16-25°C
        "max_rain_mm_day": 25.0,
        "wind_risk_kmh": 40.0,
        "growth_stages": ["sowing", "seedling", "vegetative", "bulb_development", "maturity", "harvest"],
        "water_requirement_mm": 350,
    },
    "tomato": {
        "name_hi": "टमाटर",
        "season": "rabi",
        "frost_risk_temp_c": 8.0,
        "heatwave_temp_c": 36.0,
        "max_rain_mm_day": 30.0,
        "wind_risk_kmh": 45.0,
        "growth_stages": ["nursery", "transplanting", "vegetative", "flowering", "fruiting", "harvest"],
        "water_requirement_mm": 400,
    },
}

SUPPORTED_CROPS = list(CROP_PROFILES.keys())

def get_crop_profile(crop: str) -> dict:
    crop = crop.lower().strip()
    if crop not in CROP_PROFILES:
        raise ValueError(f"Crop '{crop}' not supported. Supported: {SUPPORTED_CROPS}")
    return CROP_PROFILES[crop]
