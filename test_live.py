import requests
import json
import time

BASE_URL = "https://kisanmitra-5oqv.onrender.com"

print("================== LIVE API TESTING ==================")

# 1. Test Root / Docs
print("\n1. Testing Backend Status...")
try:
    res = requests.get(f"{BASE_URL}/docs", timeout=15)
    print(f"Docs Status: {res.status_code}")
except Exception as e:
    print(f"Failed to connect to backend: {e}")

# 2. Test Get Crops
print("\n2. Testing /crops endpoint...")
try:
    res = requests.get(f"{BASE_URL}/crops")
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
         print(f"Crops: {res.json()}")
except Exception as e:
    print(f"Failed: {e}")

# 3. Test Register Farmer
print("\n3. Testing Farmer Registration...")
farmer_payload = {
  "name": "Live Test Farmer",
  "phone": "+919999999999",
  "whatsapp": True,
  "language": "hi",
  "lat": 22.7196,
  "lon": 75.8577,
  "district": "Indore",
  "state": "Madhya Pradesh",
  "crop": "wheat",
  "growth_stage": "vegetative",
  "field_area_acres": 2.5,
  "soil_type": "loamy"
}
farmer_id = None
try:
    res = requests.post(f"{BASE_URL}/farmers/register", json=farmer_payload)
    print(f"Status: {res.status_code}")
    data = res.json()
    if res.status_code == 200:
        farmer_id = data.get("farmer_id")
        print(f"Success! Registered Farmer ID: {farmer_id}")
    elif res.status_code == 400 and "already registered" in data.get("detail", ""):
        # Extract existing ID
        import re
        match = re.search(r'Farmer ID: ([a-zA-Z0-9-]+)', data["detail"])
        if match:
            farmer_id = match.group(1)
            print(f"Farmer already existed. Re-using ID: {farmer_id}")
    else:
        print(f"Registration response: {data}")
except Exception as e:
    print(f"Failed: {e}")

# 4. Test Full Advisory Pipeline (This tests LSTM, Weather, and Groq!)
if farmer_id:
    print(f"\n4. Testing Full Advisory Pipeline for {farmer_id}...")
    try:
        res = requests.post(f"{BASE_URL}/farmers/{farmer_id}/advisory")
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            adv = res.json()
            print("Advisory pipeline success! Components:")
            print(f"  - Weather: {adv.get('weather_today', {}).get('temp_max_c')}°C")
            print(f"  - LSTM Risk: {adv.get('lstm_prediction', {}).get('source')} | 24h: {adv.get('lstm_prediction', {}).get('rainfall_mm_24h')}mm")
            irr = adv.get('irrigation_summary', {})
            print(f"  - Irrigation: {irr.get('total_volume_display')}")
            print(f"  - AI Advisory: {adv.get('ai_advisory')[:50]}...")
        else:
            print(f"Advisory failed: {res.json()}")
    except Exception as e:
         print(f"Failed: {e}")

print("\n=======================================================")
