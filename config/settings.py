from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # LLM
    anthropic_api_key: str = ""
    groz_api_key: str = ""

    # Weather APIs
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    nasa_power_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    # Twilio (kept for future)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone: str = ""
    whatsapp_from: str = "whatsapp:+14155238886"

    # Email (Gmail SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Fast2SMS
    fast2sms_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Database (Supabase PostgreSQL)
    database_url: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    alert_check_interval_minutes: int = 30
    morning_briefing_hour: int = 6

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()