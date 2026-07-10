import sys
try:
    import pypdf
    reader = pypdf.PdfReader("/Users/s0o0rya/Desktop/deep_learning.pdf")
    print(f"Pages: {len(reader.pages)}")
    print(f"Page 1: {reader.pages[0].extract_text()[:200]}")
except Exception as e:
    print(f"Error: {e}")
