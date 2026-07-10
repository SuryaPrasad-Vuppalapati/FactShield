"""Elite AI Knowledge Base (Copilot) Scraper.

Uses Gemini API (via the GEMINI_API_KEY environment variable) to generate
high-quality, technical snippets for the FactShield pipeline to entail against.
"""

from __future__ import annotations

import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

async def search_copilot(query: str) -> str:
    """Fetch an elite technical snippet from the AI Knowledge Base.
    
    Args:
        query: The user's question.
        
    Returns:
        A concise, highly factual string containing the coding/technical snippet,
        or an empty string if it fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ""
        
    try:
        client = genai.Client(api_key=api_key)
        # We ask for a concise, factual, technical snippet.
        prompt = (
            f"Provide a concise, highly factual, and technical explanation or coding snippet "
            f"for the following topic: '{query}'. "
            "Keep it under 5 sentences. Do not use conversational filler."
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        snippet = response.text.strip()
        if not snippet:
            return ""
            
        # Format it exactly like a citation so FactShield pipeline can explicitly cite it
        formatted_snippet = f"[Source: Copilot AI Knowledge Base]\n{snippet}"
        return formatted_snippet
        
    except Exception as e:
        print(f"Copilot Search Error: {e}")
        return ""
