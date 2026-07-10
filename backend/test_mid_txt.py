import sys
import io
from markitdown import MarkItDown

md = MarkItDown()
stream = io.BytesIO(b"Hello world")
result = md.convert_stream(stream, file_extension='.txt')
print("TEXT CONTENT:")
print(result.text_content)
