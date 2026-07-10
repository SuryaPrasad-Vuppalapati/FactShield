import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Tell me a very short joke about coding.'
)
print(response.text)
