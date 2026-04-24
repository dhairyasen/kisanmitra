"""
MODULE 5 — FastAPI Backend
Main application entry point.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from api.models import WeatherRequest, AdvisoryRequest, FarmerRegisterRequest, ChatbotRequest
from ingestion.weather_fetcher import get_full_weather_context, fetch_open_meteo
from models.risk_classifier import classify_risk, batch_classify
from models.irrigation_model import get_irrigation_schedule
from utils.logger import get_logger
from utils.crop_profiles import SUPPORTED_CROPS, get_crop_profile
from config.settings import get_settings

logger = get_logger("main")
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌾 KisanMitra API starting up...")
    yield
    logger.info("KisanMitra API shutting down.")

app = FastAPI(
    title="KisanMitra — Smart Weather Intelligence for Farmers",
    description="AI-powered hyperlocal weather advisory system for Indian farmers.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health Check ──────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "app": "KisanMitra",
        "version": "1.0.0",
        "supported_crops": SUPPORTED_CROPS,
        "message": "Smart Weather Intelligence for Farmers 🌾"
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}

# ── Weather Endpoints ─────────────────────────────────────────

@app.post("/weather/forecast", tags=["Weather"])
def get_forecast(req: WeatherRequest):
    """Get 7-day hyperlocal weather forecast for given coordinates."""
    data = fetch_open_meteo(req.lat, req.lon, days=req.days)
    if not data:
        raise HTTPException(status_code=503, detail="Weather API unavailable. Please try again.")
    return data

@app.post("/weather/full-context", tags=["Weather"])
def get_full_context(req: WeatherRequest):
    """Get full weather context: forecast + 30-day history."""
    return get_full_weather_context(req.lat, req.lon)

# ── Advisory Endpoints ────────────────────────────────────────

@app.post("/advisory/risk", tags=["Advisory"])
def get_risk_advisory(req: AdvisoryRequest):
    """
    Get 7-day crop risk assessment.
    Returns risks, severity scores, and actionable advisories.
    """
    weather = fetch_open_meteo(req.lat, req.lon, days=7)
    if not weather:
        raise HTTPException(status_code=503, detail="Cannot fetch weather data.")

    daily = weather.get("daily_forecast", [])
    risk_results = batch_classify(req.crop.value, req.growth_stage.value, daily)

    return {
        "crop": req.crop.value,
        "growth_stage": req.growth_stage.value,
        "location": {"lat": req.lat, "lon": req.lon},
        "risk_forecast": risk_results,
        "highest_risk_day": max(risk_results, key=lambda x: x.get("max_severity", 0), default=None)
    }

@app.post("/advisory/irrigation", tags=["Advisory"])
def get_irrigation_advisory(req: AdvisoryRequest):
    """Get 7-day smart irrigation schedule."""
    weather = fetch_open_meteo(req.lat, req.lon, days=7)
    if not weather:
        raise HTTPException(status_code=503, detail="Cannot fetch weather data.")

    daily = weather.get("daily_forecast", [])
    schedule = get_irrigation_schedule(
        crop=req.crop.value,
        growth_stage=req.growth_stage.value,
        field_area_acres=req.field_area_acres,
        daily_forecast=daily,
        soil_type=req.soil_type.value
    )
    return schedule

@app.post("/advisory/full", tags=["Advisory"])
def get_full_advisory(req: AdvisoryRequest):
    """
    Master advisory endpoint.
    Returns weather + risks + irrigation in one call.
    """
    weather = fetch_open_meteo(req.lat, req.lon, days=7)
    if not weather:
        raise HTTPException(status_code=503, detail="Cannot fetch weather data.")

    daily = weather.get("daily_forecast", [])
    risks = batch_classify(req.crop.value, req.growth_stage.value, daily)
    irrigation = get_irrigation_schedule(
        crop=req.crop.value,
        growth_stage=req.growth_stage.value,
        field_area_acres=req.field_area_acres,
        daily_forecast=daily,
        soil_type=req.soil_type.value
    )
    profile = get_crop_profile(req.crop.value)

    return {
        "status": "ok",
        "crop": req.crop.value,
        "crop_hi": profile["name_hi"],
        "growth_stage": req.growth_stage.value,
        "location": {"lat": req.lat, "lon": req.lon},
        "weather_forecast": daily,
        "risk_assessment": risks,
        "irrigation_schedule": irrigation["schedule"],
        "irrigation_summary": irrigation["summary"],
        "alert_required": any(r.get("alert_required") for r in risks)
    }

# ── Crops Info ────────────────────────────────────────────────

@app.get("/crops", tags=["Info"])
def list_crops():
    """List all supported crops with their profiles."""
    from utils.crop_profiles import CROP_PROFILES
    return {"supported_crops": SUPPORTED_CROPS, "profiles": CROP_PROFILES}

@app.get("/crops/{crop_name}", tags=["Info"])
def get_crop(crop_name: str):
    """Get detailed profile for a specific crop."""
    try:
        return get_crop_profile(crop_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api.main:app", host=settings.app_host, port=settings.app_port, reload=settings.debug)


# ── Chatbot Endpoint ──────────────────────────────────────────

@app.post("/chatbot/query", tags=["Chatbot"])
def chatbot_query(req: ChatbotRequest):
    """
    KisanMitra AI chatbot — ask anything about weather/crops.
    Powers WhatsApp bot and voice assistant.
    """
    from agents.crop_advisor_agent import quick_advisory
    from config.settings import get_settings
    cfg = get_settings()

    if not cfg.anthropic_api_key:
        return {
            "status": "no_api_key",
            "response": "AI advisory requires ANTHROPIC_API_KEY in .env file.",
            "fallback": "Please set your API key and restart."
        }

    if not req.lat or not req.lon:
        raise HTTPException(status_code=400, detail="lat and lon are required for chatbot.")

    response = quick_advisory(
        question=req.message,
        lat=req.lat,
        lon=req.lon,
        crop=req.crop.value if req.crop else "wheat",
        growth_stage=req.growth_stage.value if req.growth_stage else "vegetative",
        language=req.language.value
    )

    return {
        "status": "ok",
        "query": req.message,
        "response": response,
        "language": req.language.value
    }
