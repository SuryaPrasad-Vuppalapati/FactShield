import urllib.request
import json

url = "http://localhost:8000/api/v1/student/method-grounding"
data = {
    "question": "can you give me a hint on how to solve cost function?",
    "doc_ids": ["123e4567-e89b-12d3-a456-426614174000"],
    "chat_history": []
}

req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as res:
        body = res.read().decode('utf-8')
        print(f"Status: {res.status}")
        print(f"Body: {body}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(f"Body: {e.read().decode('utf-8')}")
