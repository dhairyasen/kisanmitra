"""
MODULE — Farmer Router
Farmer registration, profile management, and personalized advisory pipeline.
Endpoints:
  POST /farmers/register         — Register new farmer
  GET  /farmers/{id}             — Get farmer profile
  PUT  /farmers/{id}/update      — Update farmer details
  DELETE /farmers/{id}           — Delete farmer
  GET  /farmers/                 — List all farmers
  POST /farmers/{id}/advisory    — Full personalized advisory
  POST /farmers/{id}/chatbot     — Conversational QA
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from api.database import get_db
from api.schemas import Farmer
from api.models import CropEnum, GrowthStageEnum, SoilTypeEnum, LanguageEnum
from ingestion.weather_fetcher import fetch_open_meteo, get_full_weather_context
from ingestion.nasa_power import get_7day_sequence
from models.rainfall_lstm import predict_rainfall
from models.risk_classifier import classify_risk, batch_classify
from models.irrigation_model import get_irrigation_schedule
from delivery.alert_router import route_alert
from utils.logger import get_logger

logger = get_logger("farmer_router")

router = APIRouter(prefix="/farmers", tags=["Farmers"])


# ── Pydantic Request Models ───────────────────────────────────

class FarmerRegisterRequest(BaseModel):
    name:             str   = Field(..., min_length=2, max_length=100)
    phone:            str   = Field(..., pattern=r"^\+91[0-9]{10}$")
    whatsapp:         bool  = True
    language:         LanguageEnum = LanguageEnum.hi
    lat:              float = Field(..., ge=8.0,  le=37.0)
    lon:              float = Field(..., ge=68.0, le=97.0)
    district:         str
    state:            str
    crop:             CropEnum
    growth_stage:     GrowthStageEnum
    field_area_acres: float = Field(default=1.0, gt=0, le=1000)
    soil_type:        SoilTypeEnum = SoilTypeEnum.loamy
    notes:            Optional[str] = None

class FarmerUpdateRequest(BaseModel):
    name:             Optional[str]            = None
    whatsapp:         Optional[bool]           = None
    language:         Optional[LanguageEnum]   = None
    crop:             Optional[CropEnum]       = None
    growth_stage:     Optional[GrowthStageEnum]= None
    field_area_acres: Optional[float]          = None
    soil_type:        Optional[SoilTypeEnum]   = None
    notes:            Optional[str]            = None

class ChatbotRequest(BaseModel):
    message:  str
    language: Optional[LanguageEnum] = None


# ── Helper: get farmer or 404 ─────────────────────────────────

def get_farmer_or_404(farmer_id: str, db: Session) -> Farmer:
    farmer = db.query(Farmer).filter(Farmer.farmer_id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail=f"Farmer {farmer_id} not found")
    return farmer


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/register")
def register_farmer(req: FarmerRegisterRequest, db: Session = Depends(get_db)):
    """Register a new farmer in the database."""

    # Check duplicate phone
    existing = db.query(Farmer).filter(Farmer.phone == req.phone).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Phone {req.phone} already registered. Farmer ID: {existing.farmer_id}"
        )

    farmer = Farmer(
        name             = req.name,
        phone            = req.phone,
        whatsapp         = req.whatsapp,
        language         = req.language.value,
        lat              = req.lat,
        lon              = req.lon,
        district         = req.district,
        state            = req.state,
        crop             = req.crop.value,
        growth_stage     = req.growth_stage.value,
        field_area_acres = req.field_area_acres,
        soil_type        = req.soil_type.value,
        notes            = req.notes,
    )

    db.add(farmer)
    db.commit()
    db.refresh(farmer)

    logger.info(f"Farmer registered: {farmer.name} ({farmer.farmer_id}) — {farmer.crop} @ {farmer.district}")

    return {
        "status":    "registered",
        "farmer_id": farmer.farmer_id,
        "name":      farmer.name,
        "message":   f"Swagat hai {farmer.name}! KisanMitra mein aapka registration safal raha.",
    }


@router.get("/")
def list_farmers(db: Session = Depends(get_db)):
    """List all registered farmers."""
    farmers = db.query(Farmer).all()
    return {
        "total":   len(farmers),
        "farmers": [f.to_dict() for f in farmers],
    }


@router.get("/{farmer_id}")
def get_farmer(farmer_id: str, db: Session = Depends(get_db)):
    """Get farmer profile by ID."""
    farmer = get_farmer_or_404(farmer_id, db)
    return farmer.to_dict()


@router.put("/{farmer_id}/update")
def update_farmer(farmer_id: str, req: FarmerUpdateRequest, db: Session = Depends(get_db)):
    """Update farmer details."""
    farmer = get_farmer_or_404(farmer_id, db)

    if req.name             is not None: farmer.name             = req.name
    if req.whatsapp         is not None: farmer.whatsapp         = req.whatsapp
    if req.language         is not None: farmer.language         = req.language.value
    if req.crop             is not None: farmer.crop             = req.crop.value
    if req.growth_stage     is not None: farmer.growth_stage     = req.growth_stage.value
    if req.field_area_acres is not None: farmer.field_area_acres = req.field_area_acres
    if req.soil_type        is not None: farmer.soil_type        = req.soil_type.value
    if req.notes            is not None: farmer.notes            = req.notes

    db.commit()
    db.refresh(farmer)

    logger.info(f"Farmer updated: {farmer.farmer_id}")
    return {"status": "updated", "farmer": farmer.to_dict()}


@router.delete("/{farmer_id}")
def delete_farmer(farmer_id: str, db: Session = Depends(get_db)):
    """Delete a farmer."""
    farmer = get_farmer_or_404(farmer_id, db)
    db.delete(farmer)
    db.commit()
    logger.info(f"Farmer deleted: {farmer_id}")
    return {"status": "deleted", "farmer_id": farmer_id}


@router.post("/{farmer_id}/advisory")
def get_farmer_advisory(farmer_id: str, db: Session = Depends(get_db)):
    """
    Full personalized advisory pipeline for a registered farmer.
    Flow: weather → LSTM prediction → risk → irrigation → LLM advisory → alerts
    """
    farmer = get_farmer_or_404(farmer_id, db)

    lang = farmer.language

    # Step 1: Fetch current weather
    weather = fetch_open_meteo(farmer.lat, farmer.lon, days=7)
    if not weather:
        raise HTTPException(status_code=503, detail="Weather data unavailable")

    daily = weather.get("daily_forecast", [])
    today = daily[0] if daily else {}

    # Step 2: LSTM rainfall prediction using NASA POWER history
    try:
        past_7 = get_7day_sequence(farmer.lat, farmer.lon)
        rainfall_pred = predict_rainfall(past_7)
    except Exception as e:
        logger.warning(f"LSTM prediction failed: {e}, using fallback")
        rainfall_pred = {
            "rainfall_mm_24h": today.get("rainfall_mm", 0),
            "rainfall_mm_48h": today.get("rainfall_mm", 0) * 0.8,
            "rainfall_mm_72h": today.get("rainfall_mm", 0) * 0.6,
            "probability_24h": 0.3,
            "probability_48h": 0.25,
            "probability_72h": 0.2,
            "source": "fallback"
        }

    # Step 3: Risk classification
    from models.risk_classifier import classify_risk_translated
    risks = []
    for day in daily:
        result = classify_risk_translated(
            crop=farmer.crop,
            growth_stage=farmer.growth_stage,
            temp_min_c=day.get("temp_min_c"),
            temp_max_c=day.get("temp_max_c"),
            rainfall_mm=day.get("rainfall_mm", 0),
            wind_kmh=day.get("wind_max_kmh", 0),
            rainfall_prob_pct=day.get("rainfall_prob_pct", 0),
            language=lang
        )
        result["date"] = day.get("date")
        risks.append(result)

    today_risks = risks[0].get("risks", []) if risks else []
    max_severity = risks[0].get("max_severity", 0) if risks else 0

    # Step 4: Irrigation schedule
    irrigation = get_irrigation_schedule(
        crop=farmer.crop,
        growth_stage=farmer.growth_stage,
        field_area_acres=farmer.field_area_acres,
        daily_forecast=daily,
        soil_type=farmer.soil_type
    )

    # Step 5: LLM advisory
    try:
        from agents.crop_advisor_agent import quick_advisory
        from config.settings import get_settings
        cfg = get_settings()

        if cfg.anthropic_api_key:
            ai_advisory = quick_advisory(
                question=f"Give weather and crop advisory for {farmer.crop} at {farmer.growth_stage} stage in {farmer.district}",
                lat=farmer.lat,
                lon=farmer.lon,
                crop=farmer.crop,
                growth_stage=farmer.growth_stage,
                language=lang
            )
        else:
            ai_advisory = f"Apni {farmer.crop} fasal ka dhyan rakhein. Mausam par nazar rakhein."
    except Exception as e:
        logger.warning(f"LLM advisory failed: {e}")
        ai_advisory = f"Apni {farmer.crop} fasal ka dhyan rakhein."

    # Step 6: Route alerts if severity >= 2
    alert_result = {"status": "no_alert"}
    if max_severity >= 2:
        try:
            alert_result = route_alert(farmer.to_dict(), {
                "risk_type": today_risks[0].get("type", "weather") if today_risks else "weather",
                "severity":  max_severity,
                "message":   today_risks[0].get("advisory", "") if today_risks else "",
                "action":    today_risks[0].get("action", "") if today_risks else "",
            })
            # Update last alert time
            farmer.last_alert_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.warning(f"Alert routing failed: {e}")

    return {
        "status":            "ok",
        "farmer_id":         farmer_id,
        "farmer_name":       farmer.name,
        "crop":              farmer.crop,
        "district":          farmer.district,
        "language":          lang,
        "weather_today":     today,
        "lstm_prediction":   rainfall_pred,
        "risk_assessment":   risks,
        "irrigation_schedule": irrigation.get("schedule", []),
        "irrigation_summary":  irrigation.get("summary", {}),
        "ai_advisory":       ai_advisory,
        "alert_sent":        alert_result,
        "alert_required":    max_severity >= 2,
    }


@router.post("/{farmer_id}/chatbot")
def farmer_chatbot(farmer_id: str, req: ChatbotRequest, db: Session = Depends(get_db)):
    """Conversational QA chatbot for a registered farmer."""
    farmer = get_farmer_or_404(farmer_id, db)

    lang = req.language.value if req.language else farmer.language

    try:
        from agents.crop_advisor_agent import quick_advisory
        from config.settings import get_settings
        cfg = get_settings()

        if not cfg.anthropic_api_key:
            return {
                "status":   "no_api_key",
                "response": "AI advisory requires ANTHROPIC_API_KEY in .env file.",
            }

        response = quick_advisory(
            question=req.message,
            lat=farmer.lat,
            lon=farmer.lon,
            crop=farmer.crop,
            growth_stage=farmer.growth_stage,
            language=lang
        )

        return {
            "status":     "ok",
            "farmer_id":  farmer_id,
            "query":      req.message,
            "response":   response,
            "language":   lang,
        }

    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Helper for scheduler ──────────────────────────────────────

def get_all_farmers(db: Session = None):
    """Get all farmers — used by scheduler."""
    if db is None:
        from api.database import SessionLocal
        db = SessionLocal()

    farmers = db.query(Farmer).all()
    return [f.to_dict() for f in farmers]