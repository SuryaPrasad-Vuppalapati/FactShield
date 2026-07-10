from duckduckgo_search import DDGS
with DDGS() as ddgs:
    results = list(ddgs.text("how to create neural network", max_results=3))
    for r in results:
        print(f"URL: {r.get('href')} | Body: {r.get('body')[:100]}...")
