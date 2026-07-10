from app.retrieval.retriever import _get_collection
collection = _get_collection()
results = collection.get()
print(f"Total chunks in Chroma: {len(results['ids']) if results and 'ids' in results else 0}")
