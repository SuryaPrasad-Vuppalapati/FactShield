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

# Add file
data.append(f'--{boundary}')
data.append('Content-Disposition: form-data; name="file"; filename="deep_learning.pdf"')
data.append('Content-Type: application/pdf')
data.append('')
data.append('dummy pdf content')

data.append(f'--{boundary}--')
data.append('')

body = '\r\n'.join(data).encode('utf-8')

req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})

try:
    with urllib.request.urlopen(req) as res:
        print(res.read().decode('utf-8'))
except Exception as e:
    print(e.read().decode('utf-8'))
