"""
MODULE — Farmer QA Agent
Conversational chatbot with memory for registered farmers.
Farmer asks anything in their language → Claude answers with crop-specific advice.
"""

import sys
sys.path.insert(0, '.')

from typing import Optional
from utils.logger import get_logger

logger = get_logger("farmer_qa_agent")

# ── Conversation memory (in-memory per farmer) ────────────────
# Format: {farmer_id: [{"role": "user/assistant", "content": "..."}]}
_conversation_history: dict = {}
MAX_HISTORY = 10  # keep last 10 messages per farmer


def get_history(farmer_id: str) -> list:
    """Get conversation history for a farmer."""
    return _conversation_history.get(farmer_id, [])


def add_to_history(farmer_id: str, role: str, content: str):
    """Add message to farmer's conversation history."""
    if farmer_id not in _conversation_history:
        _conversation_history[farmer_id] = []

    _conversation_history[farmer_id].append({"role": role, "content": content})

    # Keep only last MAX_HISTORY messages
    if len(_conversation_history[farmer_id]) > MAX_HISTORY:
        _conversation_history[farmer_id] = _conversation_history[farmer_id][-MAX_HISTORY:]


def clear_history(farmer_id: str):
    """Clear conversation history for a farmer."""
    _conversation_history.pop(farmer_id, None)
    logger.info(f"Cleared conversation history for farmer: {farmer_id}")


def build_system_prompt(farmer: dict, language: str, weather_context: Optional[dict] = None) -> str:
    """Build personalized system prompt for a farmer."""

    lang_names = {
        "hi": "Hindi", "mr": "Marathi", "kn": "Kannada",
        "te": "Telugu", "ta": "Tamil", "pa": "Punjabi",
        "bn": "Bengali", "gu": "Gujarati", "en": "English"
    }

    lang_name = lang_names.get(language, "Hindi")

    weather_info = ""
    if weather_context:
        today = weather_context.get("daily_forecast", [{}])[0]
        weather_info = f"""
Current weather at farmer's location:
- Temperature: {today.get('temp_max_c', 'N/A')}°C (max), {today.get('temp_min_c', 'N/A')}°C (min)
- Rainfall: {today.get('rainfall_mm', 0)} mm
- Wind: {today.get('wind_max_kmh', 0)} km/h
- Rain probability: {today.get('rainfall_prob_pct', 0)}%
"""

    prompt = f"""You are KisanMitra, an expert AI agricultural advisor for Indian farmers.

FARMER PROFILE:
- Name: {farmer.get('name', 'Farmer')}
- Crop: {farmer.get('crop', 'wheat')}
- Growth stage: {farmer.get('growth_stage', 'vegetative')}
- Location: {farmer.get('district', 'India')}, {farmer.get('state', 'India')}
- Field size: {farmer.get('field_area_acres', 1)} acres
- Soil type: {farmer.get('soil_type', 'loamy')}
{weather_info}

INSTRUCTIONS:
1. ALWAYS respond in {lang_name} language only
2. Keep responses SHORT and PRACTICAL (2-4 sentences max)
3. Give specific advice based on the farmer's crop ({farmer.get('crop')}) and growth stage ({farmer.get('growth_stage')})
4. Use simple language a farmer can understand
5. If asked about irrigation, consider current weather
6. Be warm and respectful - address the farmer by name occasionally
7. Focus on actionable advice the farmer can implement today
8. Never give generic advice - always tailor to their specific crop and location

Remember: This farmer grows {farmer.get('crop')} in {farmer.get('district')}.
"""
    return prompt


def ask_farmer_agent(
    farmer_id: str,
    farmer: dict,
    message: str,
    language: str,
    weather_context: Optional[dict] = None
) -> str:
    """
    Main function — farmer asks a question, agent responds.
    Maintains conversation history per farmer.

    Args:
        farmer_id: Unique farmer ID
        farmer: Farmer profile dict
        message: Farmer's question
        language: Language code (hi/mr/kn/te/ta/pa/bn/gu/en)
        weather_context: Optional current weather data

    Returns:
        Agent's response as string
    """
    try:
        import os
        from groq import Groq
        from config.settings import get_settings

        cfg = get_settings()
        groq_key = os.getenv("GROZ_API_KEY") or os.environ.get("GROZ_API_KEY")
        if not groq_key:
            return _fallback_response(message, farmer, language)

        client = Groq(api_key=groq_key)

        # Build system prompt
        system_prompt = build_system_prompt(farmer, language, weather_context)

        # Get conversation history
        history = get_history(farmer_id)

        # Add current message to history
        add_to_history(farmer_id, "user", message)

        # Build messages for API
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]

        # Call Groq API
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            messages=messages
        )

        answer = response.choices[0].message.content.strip()

        # Save response to history
        add_to_history(farmer_id, "assistant", answer)

        logger.info(f"Farmer QA [{farmer_id}]: Q={message[:50]}... A={answer[:50]}...")
        return answer

    except Exception as e:
        logger.error(f"Farmer QA Agent error: {e}")
        return _fallback_response(message, farmer, language)


def _fallback_response(message: str, farmer: dict, language: str) -> str:
    """Fallback response when Claude API unavailable."""

    crop = farmer.get("crop", "fasal")
    name = farmer.get("name", "")

    fallbacks = {
        "hi": f"{name} ji, aapki {crop} fasal ke liye mausam par dhyan rakhein. Sinchai sahi samay par karein aur pattiyaan regularly dekhen.",
        "mr": f"{name} ji, tumchya {crop} pikaची काळजी घ्या. हवामानावर लक्ष ठेवा.",
        "kn": f"{name} ಅವರೇ, ನಿಮ್ಮ {crop} ಬೆಳೆಯ ಬಗ್ಗೆ ಗಮನ ಕೊಡಿ.",
        "te": f"{name} గారు, మీ {crop} పంటను జాగ్రత్తగా చూసుకోండి.",
        "ta": f"{name} அவர்களே, உங்கள் {crop} பயிரை கவனமாக பார்த்துக்கொள்ளுங்கள்.",
        "pa": f"{name} ji, apni {crop} fasal da dhyan rakhoh.",
        "bn": f"{name} ji, apnar {crop} fasaler jatna nin.",
        "gu": f"{name} ji, tamara {crop} pak ni sambhal rakho.",
        "en": f"{name}, please monitor your {crop} crop carefully. Check for weather changes and irrigate as needed.",
    }

    return fallbacks.get(language, fallbacks["hi"])


def get_conversation_summary(farmer_id: str) -> dict:
    """Get summary of conversation history."""
    history = get_history(farmer_id)
    return {
        "farmer_id":    farmer_id,
        "total_messages": len(history),
        "last_message": history[-1]["content"][:100] if history else None,
    }


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Farmer QA Agent...")

    dummy_farmer = {
        "farmer_id":     "test001",
        "name":          "Ramesh Kumar",
        "crop":          "wheat",
        "growth_stage":  "vegetative",
        "district":      "Indore",
        "state":         "Madhya Pradesh",
        "field_area_acres": 2.5,
        "soil_type":     "loamy",
    }

    # Test fallback (no API key needed)
    response = _fallback_response("Kya aaj sinchai karni chahiye?", dummy_farmer, "hi")
    print(f"Fallback response: {response}")

    # Test history
    add_to_history("test001", "user", "Kya aaj sinchai karni chahiye?")
    add_to_history("test001", "assistant", response)
    print(f"History: {get_history('test001')}")

    print("Farmer QA Agent ready!")