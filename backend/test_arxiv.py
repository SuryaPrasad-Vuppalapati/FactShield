import arxiv

client = arxiv.Client()
search = arxiv.Search(
  query = "neural network",
  max_results = 3,
  sort_by = arxiv.SortCriterion.Relevance
)

for r in client.results(search):
  print(f"Title: {r.title}")
  print(f"URL: {r.entry_id}")
  print(f"Summary: {r.summary[:100]}...\n")
