import urllib.request
import json
import uuid

# First, get a document id
url_docs = "http://localhost:8000/api/v1/documents"
req_docs = urllib.request.Request(url_docs)
try:
    with urllib.request.urlopen(req_docs) as res:
        docs = json.loads(res.read().decode('utf-8'))
        if docs:
            doc_id = docs[0]['id']
        else:
            print("No documents found.")
            exit(1)
except Exception as e:
    print(f"Error fetching docs: {e}")
    exit(1)

# Now test best-scored-summary
url = "http://localhost:8000/api/v1/student/best-scored-summary"
data = {
    "prompt": "Give me a quick overview of the document.",
    "doc_id": doc_id,
    "n_candidates": 2,  # Let's test with 2 candidates to make it faster
    "chat_history": []
}
data_bytes = json.dumps(data).encode('utf-8')
req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as res:
        response = json.loads(res.read().decode('utf-8'))
        print("Success! Winner score:", response['winner']['combined_score'])
        print("Total candidates:", len(response['all_candidates']))
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
