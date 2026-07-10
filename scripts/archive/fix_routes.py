import re

for file in ["backend/app/api/v1/teacher.py", "backend/app/api/v1/student.py"]:
    with open(file, "r") as f:
        content = f.read()

    # Replace OLLAMA_NOT_RUNNING check and message
    content = content.replace(
        'if result["text"] == "OLLAMA_NOT_RUNNING":',
        'if result["text"] == "AI_SERVICE_UNAVAILABLE":'
    )
    content = content.replace(
        '"response": "Local AI is not running. Please start Ollama with: ollama serve"',
        '"response": "The Hugging Face Inference API is currently unavailable or rate-limited. Please try again later or add an HF_TOKEN to your .env file."'
    )

    with open(file, "w") as f:
        f.write(content)

print("Fixed routes.")
