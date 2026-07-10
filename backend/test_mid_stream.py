import sys
import io
from markitdown import MarkItDown

md = MarkItDown()

try:
    with open('../readme.pdf', 'rb') as f:
        stream = io.BytesIO(f.read())
        # We need to know what convert_stream returns
        # Usually it returns a DocumentMetadata object that has .text_content
        result = md.convert_stream(stream, extension='.pdf')
        print("Success! First 200 chars:")
        print(result.text_content[:200])
except Exception as e:
    print(f"Error: {e}")
