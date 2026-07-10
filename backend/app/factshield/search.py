import asyncio
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

async def search_web(query: str, max_results: int = 3) -> str:
    """Perform a web search using duckduckgo_search and return snippets."""
    try:
        def _search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results

        # Run the synchronous duckduckgo_search in a background thread
        results = await asyncio.to_thread(_search)
        
        if not results:
            return ""

        context_chunks = []
        for i, res in enumerate(results):
            url = res.get('href', 'unknown-url')
            body = res.get('body', '')
            context_chunks.append(f"[Source: {url}] {body}")
            
        return "\n\n".join(context_chunks)
    except Exception as e:
        print(f"Web Search Error: {e}")
        return ""
