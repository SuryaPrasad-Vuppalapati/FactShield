
for file in ["backend/app/api/v1/teacher.py", "backend/app/api/v1/student.py"]:
    with open(file, "r") as f:
        content = f.read()

    # Replace JSONResponse(content={"error": True...
    content = content.replace(
        'JSONResponse(content={"error": True, "response": "Local AI is not running. Please start Ollama with: ollama serve"})',  # noqa: E501
        'JSONResponse(status_code=503, content={"error": True, "response": "Local AI is not running. Please start Ollama with: ollama serve"})')  # noqa: E501

    with open(file, "w") as f:
        f.write(content)

print("Fixed backend routes.")
