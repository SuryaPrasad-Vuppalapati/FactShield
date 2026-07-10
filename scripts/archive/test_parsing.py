from app.retrieval.parsing import extract_text_from_file
import sys
import os

sys.path.insert(0, os.path.abspath('backend'))

with open('readme.pdf', 'rb') as f:
    file_bytes = f.read()

try:
    text = extract_text_from_file(file_bytes, 'readme.pdf')
    print("SUCCESS!")
    print(text[:200])
except Exception as e:
    print(f"FAILED: {e}")
