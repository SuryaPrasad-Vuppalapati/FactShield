import urllib.request
import json

url = "http://localhost:8000/api/v1/documents/upload"
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
data = []

# Add owner_role
data.append(f'--{boundary}')
data.append('Content-Disposition: form-data; name="owner_role"')
data.append('')
data.append('student')

# Add real pdf file if it exists, otherwise just create a small real PDF
with open('sample.pdf', 'wb') as f:
    f.write(b'%PDF-1.4\n%\xd0\xd4\xc5\xd8\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000015 00000 n \n0000000064 00000 n \n0000000121 00000 n \n0000000227 00000 n \n0000000315 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n408\n%%EOF\n')

with open('sample.pdf', 'rb') as f:
    pdf_content = f.read()

# Build body bytes manually since it contains binary data
body_prefix = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="owner_role"\r\n\r\n'
    f'student\r\n'
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="sample.pdf"\r\n'
    f'Content-Type: application/pdf\r\n\r\n'
).encode('utf-8')

body_suffix = f'\r\n--{boundary}--\r\n'.encode('utf-8')

body = body_prefix + pdf_content + body_suffix

req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})

try:
    with urllib.request.urlopen(req) as res:
        print(res.read().decode('utf-8'))
except Exception as e:
    print("ERROR:")
    print(e.read().decode('utf-8'))
