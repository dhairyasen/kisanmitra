"""
Automated Job Scheduler using APScheduler.
Runs:
  - Daily morning briefing at 6 AM
  - Risk check every 30 minutes
  - Weekly email report every Monday 7 AM
"""

import sys
sys.path.insert(0, '.')

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from ingestion.weather_fetcher import fetch_open_meteo
from models.risk_classifier import batch_classify
from models.irrigation_model import get_irrigation_schedule
from agents.alert_composer import compose_daily_briefing
from delivery.alert_router import route_alert
from delivery.whatsapp_bot import send_whatsapp_text
from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger("scheduler")
settings = get_settings()

# In-memory farmer registry (replace with DB in production)
FARMER_REGISTRY = []


def register_farmer(farmer: dict):
    """Add a farmer to the registry for automated alerts."""
    FARMER_REGISTRY.append(farmer)
    logger.info(f"Farmer registered for alerts: {farmer.get('name')} | {farmer.get('crop')}")


def run_morning_briefing():
    """
    Runs at 6 AM daily.
    Sends personalized morning briefing to each registered farmer.
    """
    logger.info(f"Running morning briefing at {datetime.now().strftime('%H:%M')}")

    for farmer in FARMER_REGISTRY:
        try:
            lat = farmer.get("lat")
            lon = farmer.get("lon")
            crop = farmer.get("crop")
            stage = farmer.get("growth_stage")

            weather = fetch_open_meteo(lat, lon, days=7)
            if not weather:
                continue

            daily = weather["daily_forecast"]
            risks = batch_classify(crop, stage, daily)
            irrigation = get_irrigation_schedule(
                crop, stage, farmer.get("field_area_acres", 1.0), daily
            )

            # Today's data
            today_risks = risks[0] if risks else {}
            today_irrigation = irrigation["schedule"][0] if irrigation["schedule"] else {}

            message = compose_daily_briefing(crop, risks, today_irrigation, farmer.get("language", "hi"))

            if farmer.get("whatsapp"):
                send_whatsapp_text(farmer["phone"], message)

            logger.info(f"Morning briefing sent to {farmer['name']}")

        except Exception as e:
            logger.error(f"Morning briefing failed for {farmer.get('name')}: {e}")


def run_risk_check():
    """
    Runs every 30 minutes.
    Checks for extreme weather events and sends immediate alerts.
    """
    logger.info(f"Running risk check at {datetime.now().strftime('%H:%M')}")

    for farmer in FARMER_REGISTRY:
        try:
            lat = farmer.get("lat")
            lon = farmer.get("lon")
            crop = farmer.get("crop")
            stage = farmer.get("growth_stage")

            weather = fetch_open_meteo(lat, lon, days=1)
            if not weather:
                continue

            daily = weather["daily_forecast"]
            risks = batch_classify(crop, stage, daily)

            if not risks:
                continue

            today = risks[0]
            for risk in today.get("risks", []):
                if risk.get("severity", 0) >= 3:  # only alert high severity
                    route_alert(farmer, risk, crop)

        except Exception as e:
            logger.error(f"Risk check failed for {farmer.get('name')}: {e}")


def start_scheduler() -> BackgroundScheduler:
    """Initialize and start the background scheduler."""
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Daily morning briefing at 6 AM IST
    scheduler.add_job(
        run_morning_briefing,
        CronTrigger(hour=settings.morning_briefing_hour, minute=0),
        id="morning_briefing",
        name="Daily Morning Briefing",
        replace_existing=True
    )

    # Risk check every 30 minutes
    scheduler.add_job(
        run_risk_check,
        IntervalTrigger(minutes=settings.alert_check_interval_minutes),
        id="risk_check",
        name="Extreme Weather Risk Check",
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Scheduler started — Morning briefing: 6 AM | Risk check: every 30 min")
    return scheduler
