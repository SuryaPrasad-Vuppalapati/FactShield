import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_FILE_PATH = "test_doc.txt"

# Create a dummy file for upload
with open(TEST_FILE_PATH, "w") as f:
    f.write("The Nernst equation is E = E° + (RT/nF) ln(Q). It is used to calculate the cell potential of an electrochemical cell under non-standard conditions. Photosynthesis occurs primarily in the leaves.")

def test_endpoints():
    print("1. Testing Document Upload...")
    with open(TEST_FILE_PATH, "rb") as f:
        res = requests.post(f"{BASE_URL}/documents/upload", files={"file": f}, data={"owner_role": "student"})
    
    if res.status_code != 200:
        print(f"FAILED Upload: {res.status_code} - {res.text}")
        return
    
    doc_id = res.json().get("doc_id")
    print(f"SUCCESS Upload, doc_id: {doc_id}")

    endpoints = [
        ("/student/concept-guide", {"question": "Explain Nernst equation", "doc_ids": [doc_id]}),
        ("/student/problem-navigator", {"question": "I'm stuck on problem 1", "doc_ids": [doc_id]}),
        ("/student/submission-validator", {"question": "Photosynthesis is in the stems.", "doc_ids": [doc_id]}),
        ("/student/exam-simulator", {"question": "Start exam", "doc_ids": [doc_id]}),
        ("/teacher/assignment-grader", {"question": "Grade this", "context": "Photosynthesis is in leaves", "doc_ids": [doc_id]}),
        ("/teacher/exam-generator", {"question": "Create 3 questions on electrochemistry", "doc_ids": [doc_id]}),
        ("/teacher/adaptive-feedback", {"question": "Student failed question 1", "doc_ids": [doc_id]}),
        ("/teacher/learning-insights", {"question": "Show class analytics", "doc_ids": [doc_id]}),
    ]

    for endpoint, payload in endpoints:
        print(f"Testing {endpoint}...")
        try:
            res = requests.post(f"{BASE_URL}{endpoint}", json=payload)
            if res.status_code == 200:
                print(f"  SUCCESS {endpoint}")
                # print(f"  Response preview: {str(res.json())[:100]}")
            else:
                print(f"  FAILED {endpoint}: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"  ERROR {endpoint}: {e}")

if __name__ == "__main__":
    test_endpoints()
