from typing import Optional
from app.factshield.academic import search_arxiv as arxiv_search
from app.factshield.copilot import search_copilot as copilot_search
from app.factshield.search import search_web as web_search

async def search_document(query: str) -> str:
    """Searches the user's uploaded local document (syllabus/PDF) for the query.
    Always try this tool first before using any other tool.
    
    Args:
        query: The question or topic to search for in the document.
    """
    # Note: The Orchestrator intercepts this tool call and injects the document 
    # context directly, so this function body is technically never run.
    return "DOCUMENT_CONTEXT_INTERCEPTED"

async def search_arxiv(query: str) -> str:
    """Searches ArXiv for academic research papers on the topic.
    Use this if the document search fails.
    
    Args:
        query: The research topic to search for on ArXiv.
    """
    return await arxiv_search(query)

async def search_copilot(query: str) -> str:
    """Queries an elite AI Knowledge Base (Copilot) for technical or coding snippets.
    Use this if ArXiv fails or for highly technical coding questions.
    
    Args:
        query: The coding or technical question.
    """
    return await copilot_search(query)

async def search_web(query: str) -> str:
    """Scrapes the live internet via DuckDuckGo for general information.
    Use this as a last resort if all other tools fail.
    
    Args:
        query: The topic to search for on the web.
    """
    return await web_search(query)
