import urllib.request
import json

url = "http://localhost:8000/api/v1/student/method-grounding"
data = {
    "question": "give me a hint on how to use cost function",
    "doc_ids": ["691a32a6-b510-449e-b9b5-6804be47565c"],  # arbitrary valid UUID to trigger pipeline
    "chat_history": []
}

req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as res:
        print(f"Status: {res.status}")
        print(f"Response: {res.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(f"Body: {e.read().decode('utf-8')}")
