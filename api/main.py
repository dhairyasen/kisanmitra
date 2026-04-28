"""
MODULE 5 — FastAPI Backend
Main application entry point.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from api.models import WeatherRequest, AdvisoryRequest, FarmerRegisterRequest, ChatbotRequest
from api.database import create_tables
from api.farmer_router import router as farmer_router
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
    create_tables()
    logger.info("🌾 KisanMitra API starting up...")
    yield
    logger.info("KisanMitra API shutting down.")

app = FastAPI(
    title="KisanMitra — Smart Weather Intelligence for Farmers",
    description="AI-powered hyperlocal weather advisory system for Indian farmers.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ───────────────────────────────────────────
app.include_router(farmer_router)

# ── Health Check ──────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "app": "KisanMitra",
        "version": "2.0.0",
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
    Supports language parameter for multilingual responses.
    """
    from models.risk_classifier import classify_risk_translated
    from utils.translations import get_translation, get_weather_message, get_weather_advice

    weather = fetch_open_meteo(req.lat, req.lon, days=7)
    if not weather:
        raise HTTPException(status_code=503, detail="Cannot fetch weather data.")

    lang = req.language.value if req.language else "hi"
    daily = weather.get("daily_forecast", [])

    risks = []
    for day in daily:
        result = classify_risk_translated(
            crop=req.crop.value,
            growth_stage=req.growth_stage.value,
            temp_min_c=day.get("temp_min_c"),
            temp_max_c=day.get("temp_max_c"),
            rainfall_mm=day.get("rainfall_mm", 0),
            wind_kmh=day.get("wind_max_kmh", 0),
            rainfall_prob_pct=day.get("rainfall_prob_pct", 0),
            language=lang
        )
        result["date"] = day.get("date")
        risks.append(result)

    irrigation = get_irrigation_schedule(
        crop=req.crop.value,
        growth_stage=req.growth_stage.value,
        field_area_acres=req.field_area_acres,
        daily_forecast=daily,
        soil_type=req.soil_type.value
    )
    profile = get_crop_profile(req.crop.value)

    today = daily[0] if daily else {}
    weather_msg    = get_weather_message(lang, today.get("temp_max_c", 25), today.get("rainfall_mm", 0), today.get("wind_max_kmh", 0))
    weather_advice = get_weather_advice(lang, today.get("temp_max_c", 25), today.get("rainfall_mm", 0), today.get("wind_max_kmh", 0))
    ai_advisory    = get_translation(lang, "ai_advisory")

    return {
        "status":            "ok",
        "crop":              req.crop.value,
        "crop_hi":           profile["name_hi"],
        "growth_stage":      req.growth_stage.value,
        "language":          lang,
        "location":          {"lat": req.lat, "lon": req.lon},
        "weather_forecast":  daily,
        "weather_message":   weather_msg,
        "weather_advice":    weather_advice,
        "ai_advisory":       ai_advisory,
        "risk_assessment":   risks,
        "irrigation_schedule": irrigation["schedule"],
        "irrigation_summary":  irrigation["summary"],
        "alert_required":    any(r.get("alert_required") for r in risks)
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

# ── Chatbot Endpoint ──────────────────────────────────────────

@app.post("/chatbot/query", tags=["Chatbot"])
def chatbot_query(req: ChatbotRequest):
    """
    KisanMitra AI chatbot — ask anything about weather/crops.
    """
    from agents.crop_advisor_agent import quick_advisory
    from config.settings import get_settings
    cfg = get_settings()

    if not cfg.anthropic_api_key:
        return {
            "status":   "no_api_key",
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
        "status":   "ok",
        "query":    req.message,
        "response": response,
        "language": req.language.value
    }

@app.post("/advisory/report", tags=["Advisory"])
def get_advisory_report(req: AdvisoryRequest):
    """
    Generate PDF report for anonymous (non-registered) user from dashboard.
    Uses same data as /advisory/full but returns a PDF file.
    """
    from fastapi.responses import Response
    from models.risk_classifier import classify_risk_translated
    from ingestion.nasa_power import get_7day_sequence
    from models.rainfall_lstm import predict_rainfall
    from utils.pdf_generator import generate_pdf
    import os

    weather = fetch_open_meteo(req.lat, req.lon, days=7)
    if not weather:
        raise HTTPException(status_code=503, detail="Weather data unavailable")

    lang  = req.language.value if req.language else "hi"
    daily = weather.get("daily_forecast", [])

    # LSTM prediction
    try:
        past_7    = get_7day_sequence(req.lat, req.lon)
        lstm_pred = predict_rainfall(past_7)
    except Exception:
        lstm_pred = {"rainfall_mm_24h":0,"rainfall_mm_48h":0,"rainfall_mm_72h":0,
                     "probability_24h":0,"probability_48h":0,"probability_72h":0,"source":"fallback"}

    # Risk
    risks = []
    for day in daily:
        result = classify_risk_translated(
            crop=req.crop.value, growth_stage=req.growth_stage.value,
            temp_min_c=day.get("temp_min_c"), temp_max_c=day.get("temp_max_c"),
            rainfall_mm=day.get("rainfall_mm",0), wind_kmh=day.get("wind_max_kmh",0),
            rainfall_prob_pct=day.get("rainfall_prob_pct",0), language=lang
        )
        result["date"] = day.get("date")
        risks.append(result)

    # Irrigation
    irrigation = get_irrigation_schedule(
        crop=req.crop.value, growth_stage=req.growth_stage.value,
        field_area_acres=req.field_area_acres,
        daily_forecast=daily, soil_type=req.soil_type.value
    )

    # Groq advisory
    try:
        from groq import Groq
        groq_key = os.environ.get("GROZ_API_KEY") or os.getenv("GROZ_API_KEY")
        if groq_key:
            client = Groq(api_key=groq_key)
            lang_map = {"hi":"Hindi","mr":"Marathi","kn":"Kannada","te":"Telugu",
                        "ta":"Tamil","pa":"Punjabi","bn":"Bengali","gu":"Gujarati","en":"English"}
            today_w = daily[0] if daily else {}
            prompt = f"""You are KisanMitra, an expert agricultural advisor.
Crop: {req.crop.value}, Stage: {req.growth_stage.value}, Temp: {today_w.get('temp_max_c',35)}°C, Rain: {today_w.get('rainfall_mm',0)}mm.
Give 6 advisory points in {lang_map.get(lang,'Hindi')}. 4 for this week, 2 for next week. One per line, no bullets."""
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", max_tokens=400,
                messages=[{"role":"user","content":prompt}]
            )
            advisory = resp.choices[0].message.content.strip()
        else:
            advisory = f"Irrigate {req.crop.value} in early morning. Monitor temperature. Check leaves regularly."
    except Exception:
        advisory = f"Irrigate {req.crop.value} in early morning. Monitor temperature. Check leaves regularly."

    # Dummy farmer dict for PDF
    farmer_dict = {
        "farmer_id": "guest", "name": "KisanMitra User",
        "district": "India", "state": "",
        "crop": req.crop.value, "growth_stage": req.growth_stage.value,
        "field_area_acres": req.field_area_acres,
        "soil_type": req.soil_type.value, "language": lang
    }

    try:
        pdf_bytes = generate_pdf(
            farmer=farmer_dict, weather=weather, risks=risks,
            irrigation=irrigation, lstm_pred=lstm_pred,
            advisory=advisory, language=lang
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=KisanMitra_Report.pdf"}
    )


if __name__ == "__main__":
    uvicorn.run("api.main:app", host=settings.app_host, port=settings.app_port, reload=settings.debug)