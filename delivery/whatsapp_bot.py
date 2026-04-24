"""
WhatsApp Delivery via Twilio WhatsApp API.
Handles text + voice note delivery to farmers.
"""

from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger("whatsapp_bot")
settings = get_settings()


def send_whatsapp_text(to_phone: str, message: str) -> dict:
    """Send WhatsApp text message."""
    if not settings.twilio_account_sid:
        logger.info(f"[DEV] WhatsApp to {to_phone}: {message[:100]}...")
        return {"status": "dev_mode", "to": to_phone}

    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        msg = client.messages.create(
            body=message,
            from_=settings.whatsapp_from,
            to=f"whatsapp:{to_phone}"
        )

        logger.info(f"WhatsApp sent to {to_phone} | SID: {msg.sid}")
        return {"status": "sent", "sid": msg.sid, "to": to_phone}

    except Exception as e:
        logger.error(f"WhatsApp send failed to {to_phone}: {e}")
        return {"status": "failed", "error": str(e)}


def send_whatsapp_with_media(to_phone: str, message: str, media_url: str) -> dict:
    """Send WhatsApp message with image/audio attachment."""
    if not settings.twilio_account_sid:
        logger.info(f"[DEV] WhatsApp+media to {to_phone}")
        return {"status": "dev_mode"}

    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        msg = client.messages.create(
            body=message,
            from_=settings.whatsapp_from,
            to=f"whatsapp:{to_phone}",
            media_url=[media_url]
        )

        logger.info(f"WhatsApp+media sent to {to_phone} | SID: {msg.sid}")
        return {"status": "sent", "sid": msg.sid}

    except Exception as e:
        logger.error(f"WhatsApp+media failed to {to_phone}: {e}")
        return {"status": "failed", "error": str(e)}
