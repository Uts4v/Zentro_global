import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

import django
django.setup()

from django.test import Client
import json

c = Client()

# POST without auth
resp = c.post(
    '/api/pos/worker/login/',
    content_type='application/json',
    data=json.dumps({"worker_id": "00000000-0000-0000-0000-000000000000", "pin": "1234"}),
)
print('POST (no auth) Status:', resp.status_code)
print('POST (no auth) Body:', resp.content.decode())

# OPTIONS (CORS preflight)
resp = c.options(
    '/api/pos/worker/login/',
    HTTP_ORIGIN='http://localhost:8080',
    HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
    HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type',
)
print('OPTIONS Status:', resp.status_code)
print('OPTIONS Headers:', dict(resp.items()))
print('OPTIONS Body:', resp.content.decode()[:200] if resp.content else '(empty)')
