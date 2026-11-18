import urllib.request
import json

# 1. Test stats
stats = json.loads(urllib.request.urlopen('http://127.0.0.1:5000/api/stats').read())
print('Stats Response:')
print(json.dumps(stats, indent=2))

# 2. Test voters
voters = json.loads(urllib.request.urlopen('http://127.0.0.1:5000/api/voters').read())
print('\nTotal voters returned:', voters['count'])
print('\nSample First 3 voters:')
for v in voters['voters'][:3]:
    print(f"  ID: {v['id']}, Serial: {v['serial_no']}, GP#: {v['gp_serial']}, Name: {v['name']}, EPIC: {v['epic_id']}, Photo: {v['photo_path']}, Party: {v['party']}")

# 3. Test party update
req = urllib.request.Request(
    f"http://127.0.0.1:5000/api/voters/{voters['voters'][0]['id']}/party",
    data=json.dumps({'party': 'TDP'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
resp = json.loads(urllib.request.urlopen(req).read())
print('\nMarked voter 1 as TDP:', resp['success'], resp['voter']['party'])

# Reset voter 1 back to UNASSIGNED
req_reset = urllib.request.Request(
    f"http://127.0.0.1:5000/api/voters/{voters['voters'][0]['id']}/party",
    data=json.dumps({'party': 'UNASSIGNED'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
resp_reset = json.loads(urllib.request.urlopen(req_reset).read())
print('Reset voter 1 back to UNASSIGNED:', resp_reset['success'], resp_reset['voter']['party'])
