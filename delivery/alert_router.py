"""
MODULE 4 — Alert Router
Routes alerts to correct delivery channel based on severity + farmer preference.

Routing logic:
  Severity 1-2 → WhatsApp only
  Severity 3   → WhatsApp + SMS
  Severity 4   → WhatsApp + SMS + IVR call
  Severity 5   → All channels + District authority notification
"""

from delivery.sms_sender import send_sms
from delivery.whatsapp_bot import send_whatsapp_text
from agents.alert_composer import compose_alert
from utils.logger import get_logger
from datetime import datetime

logger = get_logger("alert_router")


def route_alert(farmer: dict, risk: dict, crop: str) -> dict:
    """
    Route a detected risk alert to appropriate channels.

    farmer dict must have: phone, whatsapp (bool), district, name
    risk dict from risk_classifier
    """
    severity = risk.get("severity", 0)
    if severity == 0:
        return {"status": "no_alert_needed"}

    farmer_phone = farmer.get("phone", "")
    has_whatsapp = farmer.get("whatsapp", True)
    farmer_name = farmer.get("name", "Kisan Bhai")
    district = farmer.get("district", "")

    results = {
        "farmer": farmer_name,
        "phone": farmer_phone,
        "severity": severity,
        "risk_type": risk.get("type"),
        "channels_used": [],
        "timestamp": datetime.now().isoformat()
    }

    # ── WhatsApp (severity 1+) ────────────────────────────────
    if has_whatsapp and severity >= 1:
        message = compose_alert(risk, crop, channel="whatsapp")
        result = send_whatsapp_text(farmer_phone, message)
        results["channels_used"].append("whatsapp")
        results["whatsapp"] = result

    # ── SMS (severity 3+) ─────────────────────────────────────
    if severity >= 3:
        sms_message = compose_alert(risk, crop, channel="sms")
        result = send_sms(farmer_phone, sms_message)
        results["channels_used"].append("sms")
        results["sms"] = result

    # ── IVR Voice Call (severity 4+) ──────────────────────────
    if severity >= 4:
        voice_msg = compose_alert(risk, crop, channel="voice")
        logger.warning(f"IVR CALL needed for {farmer_name} ({farmer_phone}): {voice_msg[:80]}")
        results["channels_used"].append("ivr_voice")
        results["ivr"] = {"status": "queued", "message": voice_msg}

    # ── District Authority Notification (severity 5) ──────────
    if severity == 5:
        logger.critical(
            f"EMERGENCY: Severity 5 alert for {farmer_name} in {district}. "
            f"Risk: {risk.get('type')}. District authority must be notified."
        )
        results["channels_used"].append("district_authority")
        results["emergency"] = {
            "status": "triggered",
            "district": district,
            "message": f"EMERGENCY flood/extreme weather alert for {district}"
        }

    logger.info(
        f"Alert routed: {farmer_name} | Severity {severity} | "
        f"Channels: {results['channels_used']}"
    )
    return results


def process_batch_alerts(farmers: list, daily_risks: dict, crop: str) -> list:
    """
    Process alerts for a list of farmers against their risk results.
    Called by the scheduler every 30 minutes.
    """
    results = []
    for farmer in farmers:
        farmer_risks = daily_risks.get(farmer.get("farmer_id"), {})
        risks = farmer_risks.get("risks", [])

        for risk in risks:
            if risk.get("severity", 0) >= 2:  # only alert on severity 2+
                result = route_alert(farmer, risk, crop)
                results.append(result)

    logger.info(f"Batch alerts processed: {len(results)} alerts sent to {len(farmers)} farmers")
    return results
