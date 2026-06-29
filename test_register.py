import urllib.request, json, urllib.error
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/auth/register/', 
    data=json.dumps({'email':'testm4@test.com', 'password':'SuperStrongPassword123!', 'full_name':'Test', 'role':'merchant', 'store_name':'Store'}).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}, 
    method='POST'
)
try:
    print(urllib.request.urlopen(req).read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(e.read().decode('utf-8'))
