from pypdf import PdfReader
reader = PdfReader("/Users/s0o0rya/Desktop/deep_learning.pdf")
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    if "cost function" in text.lower():
        print(f"--- Page {i+1} ---")
        print(text[:500])
