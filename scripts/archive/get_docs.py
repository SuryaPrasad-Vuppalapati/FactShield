import urllib.request

url = "http://localhost:8000/api/v1/documents"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as res:
    print(res.read().decode('utf-8'))
