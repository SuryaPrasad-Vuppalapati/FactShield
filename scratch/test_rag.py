import requests
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_FILE_PATH = "/Users/s0o0rya/Desktop/sem_3/action_learning/project/FactShield/scratch/rich_knowledge.txt"

RICH_DOCUMENT = """
Week 1 Notes: Introduction to Deep Learning
Deep learning is a subset of machine learning based on artificial neural networks. These neural networks are inspired by the structure and function of the human brain to learn patterns from vast amounts of data.

Week 2 Notes: Gradient Descent Optimization
Gradient descent is an optimization algorithm used to minimize the cost function or loss function in machine learning models. It works by iteratively updating the weights of the network in the direction of the steepest descent, defined by the negative gradient.

Week 3 Notes: Training Neural Networks with Backpropagation
Backpropagation (backward propagation of errors) is the central algorithm for training neural networks. It calculates the gradients of the loss function layer-by-layer using the chain rule, which allows the network to update its weights efficiently.
"""

def run_tests():
    # Make sure scratch dir exists
    os.makedirs(os.path.dirname(TEST_FILE_PATH), exist_ok=True)
    
    with open(TEST_FILE_PATH, "w") as f:
        f.write(RICH_DOCUMENT.strip())
        
    print("1. Uploading rich knowledge document...")
    with open(TEST_FILE_PATH, "rb") as f:
        files = {"file": (os.path.basename(TEST_FILE_PATH), f, "text/plain")}
        data = {"owner_role": "student"}
        res = requests.post(f"{BASE_URL}/documents/upload", files=files, data=data)
        
    if res.status_code != 200:
        print(f"Failed upload: {res.text}")
        return
        
    doc_id = res.json()["doc_id"]
    print(f"Doc uploaded. ID: {doc_id}")
    
    test_queries = [
        "What is deep learning?",
        "What is backpropagation?",
        "What is gradient descent?",
        "What is the capital of France?" # Irrelevant query to check similarity score relevance
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\nQuery {idx}: '{query}'")
        payload = {
            "doc_ids": [doc_id],
            "question": query
        }
        res = requests.post(f"{BASE_URL}/student/method-grounding", json=payload)
        if res.status_code == 200:
            print("Response text:")
            print(res.json()["text"])
        else:
            print(f"Failed: {res.text}")

if __name__ == "__main__":
    run_tests()
