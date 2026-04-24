"""
MODULE 3 — KisanMitra AI Agent
LangChain agent powered by Claude.
Gives crop-aware, multilingual, conversational advisory to farmers.
"""

import sys
sys.path.insert(0, '.')

from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import SystemMessage

from agents.tools import ALL_TOOLS
from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger("crop_advisor_agent")
settings = get_settings()

# ── System Prompt ─────────────────────────────────────────────

KISAN_SYSTEM_PROMPT = """You are KisanMitra — a friendly, knowledgeable agricultural AI assistant for Indian farmers.

YOUR PERSONALITY:
- Warm, helpful, like a trusted neighbor who knows farming
- Always give ACTIONABLE advice, not just data
- Use simple language — avoid technical jargon
- When you mention temperatures or measurements, always give practical context
- If a farmer asks in Hindi/regional language, respond in that language

YOUR KNOWLEDGE:
- You specialize in 7 crops: Wheat (गेहूं), Rice (चावल), Soybean (सोयाबीन), Cotton (कपास), Sugarcane (गन्ना), Onion (प्याज), Tomato (टमाटर)
- You understand Indian farming seasons: Kharif (June-Oct) and Rabi (Nov-Mar)
- You know Indian states, districts, and local farming conditions
- If unsure about something, recommend consulting the local Krishi Vigyan Kendra (KVK)

FARMER CONTEXT:
- Crop: {crop}
- Growth Stage: {growth_stage}  
- Location: {district}, {state}
- Field Area: {field_area} acres
- Soil Type: {soil_type}

TOOLS AVAILABLE:
- Use get_weather_forecast to check current weather before giving advice
- Use get_crop_risk to detect dangers for the farmer's specific crop
- Use get_irrigation_advice for irrigation scheduling
- Use get_crop_info for crop-specific thresholds

IMPORTANT RULES:
1. Always check weather FIRST before giving crop advice
2. Give specific, actionable steps (not vague advice)
3. Mention timing (e.g., "irrigate between 5-7 AM")
4. If severity is high (3+), emphasize urgency clearly
5. End each response with one key action the farmer should take TODAY
"""

LANGUAGE_PROMPTS = {
    "hi": "Respond in simple Hindi (हिंदी में जवाब दें). Use easy words a farmer would understand.",
    "mr": "Respond in simple Marathi (मराठीत उत्तर द्या).",
    "kn": "Respond in simple Kannada (ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ).",
    "te": "Respond in simple Telugu (తెలుగులో సమాధానం ఇవ్వండి).",
    "ta": "Respond in simple Tamil (தமிழில் பதில் கூறுங்கள்).",
    "pa": "Respond in simple Punjabi (ਪੰਜਾਬੀ ਵਿੱਚ ਜਵਾਬ ਦਿਓ).",
    "bn": "Respond in simple Bengali (বাংলায় উত্তর দিন).",
    "en": "Respond in simple English."
}


def create_kisan_agent(
    crop: str = "wheat",
    growth_stage: str = "vegetative",
    district: str = "Unknown",
    state: str = "India",
    field_area: float = 1.0,
    soil_type: str = "loamy",
    language: str = "hi"
):
    """
    Create a personalized KisanMitra agent for a specific farmer.
    Returns AgentExecutor ready to chat.
    """
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env file")

    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.3,
        max_tokens=1024
    )

    # Build personalized system prompt
    lang_instruction = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["hi"])
    system_content = KISAN_SYSTEM_PROMPT.format(
        crop=crop,
        growth_stage=growth_stage,
        district=district,
        state=state,
        field_area=field_area,
        soil_type=soil_type
    ) + f"\n\nLANGUAGE INSTRUCTION: {lang_instruction}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_content),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)

    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        return_messages=True,
        k=10  # remember last 10 exchanges
    )

    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        memory=memory,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True
    )

    logger.info(f"KisanMitra agent created for {crop} | {district}, {state} | Language: {language}")
    return executor


def quick_advisory(
    question: str,
    lat: float,
    lon: float,
    crop: str,
    growth_stage: str,
    language: str = "hi"
) -> str:
    """
    One-shot advisory without memory.
    Good for WhatsApp/SMS single-query responses.
    """
    agent = create_kisan_agent(crop=crop, growth_stage=growth_stage, language=language)
    
    # Embed coordinates in the question so agent can use tools
    enriched_question = f"{question} [My location coordinates: {lat},{lon}]"
    
    try:
        result = agent.invoke({"input": enriched_question})
        return result.get("output", "Could not generate advisory.")
    except Exception as e:
        logger.error(f"quick_advisory error: {e}")
        return f"Advisory service temporarily unavailable. Please try again."
