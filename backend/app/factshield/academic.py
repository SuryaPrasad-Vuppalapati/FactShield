import asyncio
import arxiv

async def search_arxiv(query: str, max_results: int = 3) -> str:
    """Perform an academic search using arxiv and return abstracts."""
    try:
        def _search():
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            return list(client.results(search))

        # Run the synchronous arxiv search in a background thread
        results = await asyncio.to_thread(_search)
        
        if not results:
            return ""

        context_chunks = []
        for i, res in enumerate(results):
            # Use PDF URL so citations link directly to the paper PDF
            url = res.pdf_url or res.entry_id.replace("/abs/", "/pdf/")
            title = res.title
            abstract = res.summary.replace("\n", " ")
            context_chunks.append(f"[Source: {url}]\nTitle: {title}\nAbstract: {abstract}")
            
        return "\n\n".join(context_chunks)
    except Exception as e:
        print(f"ArXiv Search Error: {e}")
        return ""
