import urllib.request
import json
import uuid

def upload_dummy_doc(content: str, filename: str):
    url = "http://localhost:8000/api/v1/documents/upload"
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    data = []

    # Add owner_role
    data.append(f'--{boundary}')
    data.append('Content-Disposition: form-data; name="owner_role"')
    data.append('')
    data.append('student')

    # Add file
    data.append(f'--{boundary}')
    data.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
    data.append('Content-Type: text/plain')
    data.append('')
    data.append(content)

    data.append(f'--{boundary}--')
    data.append('')

    body = '\r\n'.join(data).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        with urllib.request.urlopen(req) as res:
            response = json.loads(res.read().decode('utf-8'))
            return response['doc_id']
    except Exception as e:
        print(f"Upload failed: {e}")
        return None

def test_summary(doc_id):
    url = "http://localhost:8000/api/v1/student/best-scored-summary"
    data = {
        "prompt": "Give me a quick overview of the document.",
        "doc_id": doc_id,
        "n_candidates": 1,
        "chat_history": []
    }
    data_bytes = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as res:
            response = json.loads(res.read().decode('utf-8'))
            return response['winner']['text']
    except Exception as e:
        print(f"Summary failed: {e}")
        return None

# Upload biology doc
bio_id = upload_dummy_doc("Biology is the study of life. It encompasses cellular biology, genetics, and ecology. Animals and plants are studied.", "biology.txt")
print("Bio ID:", bio_id)
if bio_id:
    print("Bio Summary:", test_summary(bio_id))

# Upload math doc
math_id = upload_dummy_doc("Mathematics includes algebra, calculus, and geometry. Numbers and formulas are fundamental.", "math.txt")
print("Math ID:", math_id)
if math_id:
    print("Math Summary:", test_summary(math_id))

