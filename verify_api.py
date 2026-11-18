import urllib.request
import json

for q in ['130', '135', '180', '186', '187', '222']:
    url = f'http://localhost:5000/api/voters?search={q}'
    data = json.loads(urllib.request.urlopen(url).read().decode())
    print(f"=== Search: {q} ===")
    for v in data['voters']:
        if str(v['gp_serial']) == q:
            print(f"GP#{v['gp_serial']} | Name: {v['name']} | Rel: {v['relation_type']} {v['relation_name']} | Gender: {v['gender']} | House: {v['house_no']} | Photo: {v['photo_path']}")
