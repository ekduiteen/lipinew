"""Heritage prompt generator for targeted dialect and register data collection."""

import logging
from typing import Optional
import httpx

logger = logging.getLogger("lipi.backend.heritage_prompt")

# Starter prompts for each heritage mode
STARTER_PROMPTS = {
    "STORY": {
        "en": "Tell me a favorite story or memory from your childhood or community.",
        "ne": "तपाईंको बचपन वा समुदायको एक मनपर्ने कथा वा स्मृति बताउनुहोस्।",
    },
    "WORD_EXPLANATION": {
        "en": "Explain a word or phrase that's important in your local culture or dialect.",
        "ne": "तपाईंको स्थानीय संस्कृति वा भाषिकामा महत्त्वपूर्ण एक शब्द वा वाक्यांश व्याख्या गर्नुहोस्।",
    },
    "CULTURE": {
        "en": "Describe a cultural practice, tradition, or celebration that's unique to your region.",
        "ne": "तपाईंको क्षेत्रमा अद्वितीय एक सांस्कृतिक अभ्यास, परम्परा, वा उत्सव वर्णन गर्नुहोस्।",
    },
    "PROVERB": {
        "en": "Share a local proverb or saying and explain what it means.",
        "ne": "एक स्थानीय उखान वा कहावत साझा गर्नुहोस् र यसको अर्थ व्याख्या गर्नुहोस्।",
    },
    "VARIATION": {
        "en": "Say the same sentence in different ways—casual, formal, respectful, with elders.",
        "ne": "एउटै वाक्यलाई विभिन्न तरिकाले भन्नुहोस्—अनौपचारिक, औपचारिक, सम्मानपूर्ण, ज्येष्ठहरूसँग।",
    },
}

# Follow-up prompts (context-aware)
FOLLOWUP_TEMPLATES = {
    "STORY": {
        "en": "What lesson or meaning did this story have for you?",
        "ne": "यस कथाको तपाईंको लागि के सिख वा अर्थ थियो?",
    },
    "WORD_EXPLANATION": {
        "en": "Can you use this word in a sentence the way people in your community would?",
        "ne": "के तपाई यस शब्दलाई वाक्यमा प्रयोग गर्न सक्नुहुन्छ जसरी तपाईंको समुदायका मानिसहरूले गर्दछन्?",
    },
    "CULTURE": {
        "en": "When and why is this practice still important in your region?",
        "ne": "यो अभ्यास कहिले र किन तपाईंको क्षेत्रमा अझै महत्त्वपूर्ण छ?",
    },
    "PROVERB": {
        "en": "Can you give an example of when you'd use this saying?",
        "ne": "के तपाई दिन सक्नुहुन्छ कहिले तपाई यो कहावत प्रयोग गर्नुहुन्छ त्यसको उदाहरण?",
    },
    "VARIATION": {
        "en": "Which version is the most natural for you, and why?",
        "ne": "तपाईंको लागि कुन संस्करण सबैभन्दा प्राकृतिक छ, र किन?",
    },
}


async def generate_starter_prompt(
    http_client: Optional[httpx.AsyncClient], language: str, mode: str
) -> str:
    """
    Generate a starter prompt for heritage session.

    Args:
        http_client: async HTTP client (unused here, kept for future LLM integration)
        language: 'nepali' or 'english'
        mode: STORY, WORD_EXPLANATION, CULTURE, PROVERB, VARIATION

    Returns:
        The starter prompt text in the requested language.
    """
    prompts = STARTER_PROMPTS.get(mode, STARTER_PROMPTS["STORY"])
    lang_key = "ne" if language == "nepali" else "en"
    return prompts.get(lang_key, prompts.get("en", "Tell me something about your language."))


async def generate_follow_up(
    http_client: Optional[httpx.AsyncClient],
    language: str,
    mode: str,
    response_text: str,
) -> str:
    """
    Generate a follow-up prompt based on mode and user response.

    Args:
        http_client: async HTTP client (unused here, kept for future LLM integration)
        language: 'nepali' or 'english'
        mode: STORY, WORD_EXPLANATION, CULTURE, PROVERB, VARIATION
        response_text: user's response to the starter prompt

    Returns:
        The follow-up prompt text.
    """
    templates = FOLLOWUP_TEMPLATES.get(mode, FOLLOWUP_TEMPLATES["STORY"])
    lang_key = "ne" if language == "nepali" else "en"
    return templates.get(lang_key, templates.get("en", "Tell me more."))
