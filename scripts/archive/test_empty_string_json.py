import json

try:
    print(json.loads('{"text": ""}'))
except Exception as e:
    print(e)
