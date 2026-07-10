import os

path = "backend/app/factshield/generation.py"
with open(path, "r") as f:
    content = f.read()

content = content.replace(
    'return response.choices[0].message.content',
    'content = response.choices[0].message.content\n        if not content:\n            return "AI_SERVICE_UNAVAILABLE"\n        return content'
)

with open(path, "w") as f:
    f.write(content)
print("Fixed generation.py")
