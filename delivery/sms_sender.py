"""
SMS Delivery via Twilio.
Handles sending alerts to farmers without WhatsApp.
"""

from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger("sms_sender")
settings = get_settings()


def send_sms(to_phone: str, message: str) -> dict:
    """
    Send SMS via Twilio.
    Returns delivery status.
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio credentials not set. SMS not sent (dev mode).")
        logger.info(f"[DEV] SMS to {to_phone}: {message[:80]}...")
        return {"status": "dev_mode", "to": to_phone, "message_preview": message[:80]}

    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        msg = client.messages.create(
            body=message[:160],  # SMS character limit
            from_=settings.twilio_phone,
            to=to_phone
        )

        logger.info(f"SMS sent to {to_phone} | SID: {msg.sid}")
        return {"status": "sent", "sid": msg.sid, "to": to_phone}

    except Exception as e:
        logger.error(f"SMS send failed to {to_phone}: {e}")
        return {"status": "failed", "error": str(e), "to": to_phone}
