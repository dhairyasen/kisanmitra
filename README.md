# 🌾 KisanMitra — Smart Weather Intelligence for Farmers

> AI-powered hyperlocal weather advisory system for Indian farmers.
> Smart India Hackathon | Statement 2

## Quick Start (Windows)

```bash
# 1. Clone and enter project
cd kisanmitra

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
copy .env.example .env
# Edit .env and add your API keys

# 5. Run the server
python run.py
```

## API Docs
Visit: http://localhost:8000/docs

## Supported Crops
Wheat, Rice, Soybean, Cotton, Sugarcane, Onion, Tomato

## Tech Stack
- FastAPI + Python 3.10
- Open-Meteo API (free, no key needed)
- NASA POWER API (free, no key needed)
- XGBoost + TensorFlow (ML)
- LangChain + Claude API (AI Advisory)
- Twilio (SMS + WhatsApp)
- APScheduler (Automated alerts)
