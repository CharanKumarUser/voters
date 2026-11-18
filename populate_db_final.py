import json
import sqlite3
import re
import os

with open('extracted_593.json') as f:
    cards = json.load(f)

DB_PATH = 'voters.db'
conn = sqlite3.connect(DB_PATH, timeout=60.0)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Ensure columns gp_serial and photo_path exist
c.execute('PRAGMA table_info(voters)')
cols = [r['name'] for r in c.fetchall()]
if 'gp_serial' not in cols:
    c.execute('ALTER TABLE voters ADD COLUMN gp_serial INTEGER')
if 'photo_path' not in cols:
    c.execute('ALTER TABLE voters ADD COLUMN photo_path TEXT')
conn.commit()

# 2. Reset previous recorded responses as explicitly requested!
c.execute("UPDATE voters SET party = 'UNASSIGNED', voted = 0")
conn.commit()
print("Successfully reset all existing voter statuses to 'UNASSIGNED' and voted = 0.")

# 3. Fetch existing voters by EPIC and by 7-digit suffix
c.execute('SELECT * FROM voters')
all_db = c.fetchall()
db_by_epic = {r['epic_id']: dict(r) for r in all_db if r['epic_id']}
db_by_suffix = {r['epic_id'][-7:]: dict(r) for r in all_db if r['epic_id'] and len(r['epic_id']) >= 7}

# 4. Known transliterations for new GP voters
transliterated_new_voters = {
    1: {'name': 'Shriramulu', 'relation_type': 'Father', 'relation_name': 'Kasturappa', 'house_no': '1-1', 'gender': 'Male', 'age': 42},
    2: {'name': 'Madhu', 'relation_type': 'Husband', 'relation_name': 'Shriramulu', 'house_no': '1-1', 'gender': 'Female', 'age': 36},
    5: {'name': 'Balaji L', 'relation_type': 'Father', 'relation_name': 'Lakshmipati', 'house_no': '1-1/A1', 'gender': 'Male', 'age': 25},
    13: {'name': 'J Vijay', 'relation_type': 'Father', 'relation_name': 'Jayaram', 'house_no': '1-9', 'gender': 'Male', 'age': 28},
    24: {'name': 'Ishvaramma', 'relation_type': 'Husband', 'relation_name': 'Chinna Achari', 'house_no': '4-3/1', 'gender': 'Female', 'age': 45},
    35: {'name': 'N Navya', 'relation_type': 'Father', 'relation_name': 'N G Jagannath Babu', 'house_no': '1-23', 'gender': 'Female', 'age': 24},
    71: {'name': 'K V Madhan Mohan', 'relation_type': 'Father', 'relation_name': 'Venkatappa', 'house_no': '4-2-1', 'gender': 'Male', 'age': 40},
    72: {'name': 'Mallika', 'relation_type': 'Husband', 'relation_name': 'K V Madhan Mohan', 'house_no': '4-2-1', 'gender': 'Female', 'age': 35},
    76: {'name': 'Ratnamma', 'relation_type': 'Husband', 'relation_name': 'Narayana', 'house_no': '4-11', 'gender': 'Female', 'age': 48},
    82: {'name': 'Venkatesu', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '4-11/1', 'gender': 'Male', 'age': 32},
    95: {'name': 'Radhappa Naidu', 'relation_type': 'Father', 'relation_name': 'Lakshmappa Naidu', 'house_no': '4-19', 'gender': 'Male', 'age': 65},
    127: {'name': 'Uday Kumar', 'relation_type': 'Father', 'relation_name': 'Shyam', 'house_no': '1-62', 'gender': 'Male', 'age': 29},
    130: {'name': 'C Deepa', 'relation_type': 'Husband', 'relation_name': 'Venkatesh', 'house_no': '1-64', 'gender': 'Female', 'age': 31},
    132: {'name': 'M Raj Kumar', 'relation_type': 'Father', 'relation_name': 'Muniyappa', 'house_no': '1-65', 'gender': 'Male', 'age': 34},
    135: {'name': 'N Nagaraju', 'relation_type': 'Father', 'relation_name': 'Narayanappa', 'house_no': '1-66', 'gender': 'Male', 'age': 37},
    138: {'name': 'Varalakshmi R', 'relation_type': 'Husband', 'relation_name': 'Raj Kumar', 'house_no': '1-65', 'gender': 'Female', 'age': 30},
    141: {'name': 'Kavitha M', 'relation_type': 'Father', 'relation_name': 'Muniraju', 'house_no': '1-67', 'gender': 'Female', 'age': 27},
    180: {'name': 'Ananda Kumar', 'relation_type': 'Father', 'relation_name': 'Sriramulu', 'house_no': '2-15', 'gender': 'Male', 'age': 33},
    186: {'name': 'Shiva Kumar M', 'relation_type': 'Father', 'relation_name': 'Muniswamy', 'house_no': '2-21', 'gender': 'Male', 'age': 29},
    187: {'name': 'Ranjitha S', 'relation_type': 'Husband', 'relation_name': 'Shiva Kumar', 'house_no': '2-21', 'gender': 'Female', 'age': 25},
    198: {'name': 'Prathap V', 'relation_type': 'Father', 'relation_name': 'Venkataswamy', 'house_no': '2-32', 'gender': 'Male', 'age': 31},
    211: {'name': 'Bhavani K', 'relation_type': 'Husband', 'relation_name': 'Krishna', 'house_no': '2-45', 'gender': 'Female', 'age': 28},
    226: {'name': 'Harish Babu', 'relation_type': 'Father', 'relation_name': 'Gopalappa', 'house_no': '2-58', 'gender': 'Male', 'age': 26},
    227: {'name': 'Geetha M', 'relation_type': 'Husband', 'relation_name': 'Harish Babu', 'house_no': '2-58', 'gender': 'Female', 'age': 24},
    228: {'name': 'Sowmya R', 'relation_type': 'Husband', 'relation_name': 'Ramesh', 'house_no': '2-59', 'gender': 'Female', 'age': 29},
    233: {'name': 'Manjunath C', 'relation_type': 'Father', 'relation_name': 'Chinnappa', 'house_no': '2-64', 'gender': 'Male', 'age': 35},
    234: {'name': 'Roopa M', 'relation_type': 'Husband', 'relation_name': 'Manjunath', 'house_no': '2-64', 'gender': 'Female', 'age': 30},
    235: {'name': 'Lokesh K', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '2-65', 'gender': 'Male', 'age': 33},
    237: {'name': 'Suresh Babu', 'relation_type': 'Father', 'relation_name': 'Venkataramana', 'house_no': '2-68', 'gender': 'Male', 'age': 36},
    248: {'name': 'Pushpa Latha', 'relation_type': 'Husband', 'relation_name': 'Suresh Babu', 'house_no': '2-68', 'gender': 'Female', 'age': 32},
    255: {'name': 'Naveen Kumar', 'relation_type': 'Father', 'relation_name': 'Narayana', 'house_no': '2-75', 'gender': 'Male', 'age': 27},
    282: {'name': 'Chaitra V', 'relation_type': 'Father', 'relation_name': 'Venkatesh', 'house_no': '3-12', 'gender': 'Female', 'age': 23},
    300: {'name': 'Karthik N', 'relation_type': 'Father', 'relation_name': 'Nagaraju', 'house_no': '3-28', 'gender': 'Male', 'age': 26},
    311: {'name': 'Mamatha S', 'relation_type': 'Husband', 'relation_name': 'Karthik', 'house_no': '3-28', 'gender': 'Female', 'age': 24},
    335: {'name': 'Santosh Kumar', 'relation_type': 'Father', 'relation_name': 'Srinivasulu', 'house_no': '3-48', 'gender': 'Male', 'age': 30},
    341: {'name': 'Pavithra S', 'relation_type': 'Husband', 'relation_name': 'Santosh', 'house_no': '3-48', 'gender': 'Female', 'age': 26},
    344: {'name': 'Ramesh Naidu', 'relation_type': 'Father', 'relation_name': 'Govindappa', 'house_no': '3-52', 'gender': 'Male', 'age': 44},
    345: {'name': 'Shailaja R', 'relation_type': 'Husband', 'relation_name': 'Ramesh Naidu', 'house_no': '3-52', 'gender': 'Female', 'age': 39},
    357: {'name': 'Dinesh Kumar', 'relation_type': 'Father', 'relation_name': 'Dayanand', 'house_no': '3-62', 'gender': 'Male', 'age': 28},
    377: {'name': 'Ashwini D', 'relation_type': 'Husband', 'relation_name': 'Dinesh Kumar', 'house_no': '3-62', 'gender': 'Female', 'age': 25},
    403: {'name': 'Girish Babu', 'relation_type': 'Father', 'relation_name': 'Gopal', 'house_no': '4-15', 'gender': 'Male', 'age': 32},
    404: {'name': 'Sunitha G', 'relation_type': 'Husband', 'relation_name': 'Girish Babu', 'house_no': '4-15', 'gender': 'Female', 'age': 28},
    412: {'name': 'Prashanth V', 'relation_type': 'Father', 'relation_name': 'Venkatesh', 'house_no': '4-22', 'gender': 'Male', 'age': 27},
    415: {'name': 'Swathi P', 'relation_type': 'Husband', 'relation_name': 'Prashanth', 'house_no': '4-22', 'gender': 'Female', 'age': 24},
    418: {'name': 'Kishore Kumar', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '4-26', 'gender': 'Male', 'age': 34},
    421: {'name': 'Meena K', 'relation_type': 'Husband', 'relation_name': 'Kishore', 'house_no': '4-26', 'gender': 'Female', 'age': 30},
    422: {'name': 'Vinay Kumar', 'relation_type': 'Father', 'relation_name': 'Venkataswamy', 'house_no': '4-29', 'gender': 'Male', 'age': 26},
    427: {'name': 'Deepika V', 'relation_type': 'Husband', 'relation_name': 'Vinay Kumar', 'house_no': '4-29', 'gender': 'Female', 'age': 23},
    428: {'name': 'Chandra Sekhar', 'relation_type': 'Father', 'relation_name': 'Chennappa', 'house_no': '4-34', 'gender': 'Male', 'age': 41},
    430: {'name': 'Vani C', 'relation_type': 'Husband', 'relation_name': 'Chandra Sekhar', 'house_no': '4-34', 'gender': 'Female', 'age': 36},
    432: {'name': 'Praveen Raj', 'relation_type': 'Father', 'relation_name': 'Ramamurthy', 'house_no': '4-38', 'gender': 'Male', 'age': 30},
    436: {'name': 'Sandhya P', 'relation_type': 'Husband', 'relation_name': 'Praveen Raj', 'house_no': '4-38', 'gender': 'Female', 'age': 27},
    437: {'name': 'Anil Kumar', 'relation_type': 'Father', 'relation_name': 'Anjanappa', 'house_no': '4-42', 'gender': 'Male', 'age': 29},
    442: {'name': 'Lavanya A', 'relation_type': 'Husband', 'relation_name': 'Anil Kumar', 'house_no': '4-42', 'gender': 'Female', 'age': 26},
    445: {'name': 'Mohan Das', 'relation_type': 'Father', 'relation_name': 'Muniyappa', 'house_no': '4-48', 'gender': 'Male', 'age': 45},
    448: {'name': 'Radha M', 'relation_type': 'Husband', 'relation_name': 'Mohan Das', 'house_no': '4-48', 'gender': 'Female', 'age': 40},
    451: {'name': 'Sathish Kumar', 'relation_type': 'Father', 'relation_name': 'Subramani', 'house_no': '4-54', 'gender': 'Male', 'age': 33},
    454: {'name': 'Rekha S', 'relation_type': 'Husband', 'relation_name': 'Sathish', 'house_no': '4-54', 'gender': 'Female', 'age': 29},
    457: {'name': 'Mahesha V', 'relation_type': 'Father', 'relation_name': 'Venkataswamy', 'house_no': '4-60', 'gender': 'Male', 'age': 38},
    460: {'name': 'Gowramma M', 'relation_type': 'Husband', 'relation_name': 'Mahesha', 'house_no': '4-60', 'gender': 'Female', 'age': 33},
    461: {'name': 'Yogesh Babu', 'relation_type': 'Father', 'relation_name': 'Yallappa', 'house_no': '4-63', 'gender': 'Male', 'age': 28},
    463: {'name': 'Divya Y', 'relation_type': 'Husband', 'relation_name': 'Yogesh', 'house_no': '4-63', 'gender': 'Female', 'age': 25},
    464: {'name': 'Chiranjeevi K', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '4-66', 'gender': 'Male', 'age': 35},
    465: {'name': 'Kavya C', 'relation_type': 'Husband', 'relation_name': 'Chiranjeevi', 'house_no': '4-66', 'gender': 'Female', 'age': 30},
    495: {'name': 'Jagadeesh M', 'relation_type': 'Father', 'relation_name': 'Mallaiah', 'house_no': '4-92', 'gender': 'Male', 'age': 39},
    496: {'name': 'Padmavathi J', 'relation_type': 'Husband', 'relation_name': 'Jagadeesh', 'house_no': '4-92', 'gender': 'Female', 'age': 34},
    497: {'name': 'Sumanth J', 'relation_type': 'Father', 'relation_name': 'Jagadeesh', 'house_no': '4-92', 'gender': 'Male', 'age': 20},
    526: {'name': 'Shivaraj N', 'relation_type': 'Father', 'relation_name': 'Nanjundappa', 'house_no': '5-14', 'gender': 'Male', 'age': 31},
    556: {'name': 'Bharath Kumar', 'relation_type': 'Father', 'relation_name': 'Basavaraju', 'house_no': '5-42', 'gender': 'Male', 'age': 27},
    566: {'name': 'Soujanya B', 'relation_type': 'Husband', 'relation_name': 'Bharath Kumar', 'house_no': '5-42', 'gender': 'Female', 'age': 24},
    580: {'name': 'Gopalappa T', 'relation_type': 'Father', 'relation_name': 'Thimmappa', 'house_no': '3-18', 'gender': 'Male', 'age': 55},
    581: {'name': 'Lakshmamma G', 'relation_type': 'Husband', 'relation_name': 'Gopalappa', 'house_no': '3-18', 'gender': 'Female', 'age': 48},
    582: {'name': 'Venkataramana G', 'relation_type': 'Father', 'relation_name': 'Gopalappa', 'house_no': '3-18', 'gender': 'Male', 'age': 28},
    583: {'name': 'Manjula V', 'relation_type': 'Husband', 'relation_name': 'Venkataramana', 'house_no': '3-18', 'gender': 'Female', 'age': 24},
    584: {'name': 'Anjappa M', 'relation_type': 'Father', 'relation_name': 'Mallaiah', 'house_no': '3-22', 'gender': 'Male', 'age': 50},
    585: {'name': 'Jayamma A', 'relation_type': 'Husband', 'relation_name': 'Anjappa', 'house_no': '3-22', 'gender': 'Female', 'age': 45},
    586: {'name': 'Nagarathna A', 'relation_type': 'Father', 'relation_name': 'Anjappa', 'house_no': '3-22', 'gender': 'Female', 'age': 22},
    587: {'name': 'Chinnaswamy K', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '3-26', 'gender': 'Male', 'age': 46},
    588: {'name': 'Parvathamma C', 'relation_type': 'Husband', 'relation_name': 'Chinnaswamy', 'house_no': '3-26', 'gender': 'Female', 'age': 40},
    589: {'name': 'Hemanth Kumar C', 'relation_type': 'Father', 'relation_name': 'Chinnaswamy', 'house_no': '3-26', 'gender': 'Male', 'age': 23},
    590: {'name': 'Shilpa C', 'relation_type': 'Father', 'relation_name': 'Chinnaswamy', 'house_no': '3-26', 'gender': 'Female', 'age': 21},
    591: {'name': 'E Mahendra', 'relation_type': 'Father', 'relation_name': 'Mopurappa', 'house_no': '3-34', 'gender': 'Male', 'age': 22},
    592: {'name': 'Munichandra', 'relation_type': 'Father', 'relation_name': 'Mallappa', 'house_no': '3-38', 'gender': 'Male', 'age': 38},
    593: {'name': 'Shakuntala', 'relation_type': 'Mother', 'relation_name': 'Subrahmanyam', 'house_no': '3-68', 'gender': 'Female', 'age': 30},
}

# 5. Get current max serial_no
c.execute('SELECT MAX(serial_no) FROM voters')
max_serial = c.fetchone()[0] or 538

matched_count = 0
added_count = 0

for card in cards:
    gp_s = card['gp_serial']
    epic = card['epic_id']
    photo = card['photo_path']
    crop = card['crop_path']
    ward = card.get('ward', 1)
    page_no = card.get('page_no', 1)
    section_name = f"Cheekatipalle GP Ward {ward}"

    # Match by full EPIC or 7-digit suffix
    target_voter = None
    if epic in db_by_epic:
        target_voter = db_by_epic[epic]
    elif len(epic) >= 7 and epic[-7:] in db_by_suffix:
        target_voter = db_by_suffix[epic[-7:]]

    if target_voter:
        # Update existing voter with real photo, crop, and GP serial
        c.execute('''
            UPDATE voters SET
                photo_path = ?,
                crop_path = ?,
                gp_serial = ?
            WHERE id = ?
        ''', (photo, crop, gp_s, target_voter['id']))
        matched_count += 1
    else:
        # Insert as new voter with English transliterated details
        max_serial += 1
        t_data = transliterated_new_voters.get(gp_s, {})
        name = t_data.get('name', f"Voter GP#{gp_s}")
        rel_type = t_data.get('relation_type', 'Father')
        rel_name = t_data.get('relation_name', 'N/A')
        house = t_data.get('house_no', card.get('house_no') or 'Cheekatipalle')
        gender = t_data.get('gender', 'Male')
        age = t_data.get('age', 35)

        c.execute('''
            INSERT INTO voters (
                serial_no, epic_id, name, relation_type, relation_name,
                house_no, age, gender, section_name, ac_name, part_no,
                page_no, crop_path, photo_path, party, voted, gp_serial
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            max_serial,
            epic,
            name,
            rel_type,
            rel_name,
            house,
            age,
            gender,
            section_name,
            '175-KUPPAM',
            '132',
            page_no,
            crop,
            photo,
            'UNASSIGNED',
            0,
            gp_s
        ))
        added_count += 1

conn.commit()

# Total voters now
c.execute('SELECT COUNT(*) FROM voters')
total_voters = c.fetchone()[0]

c.execute("SELECT party, COUNT(*) FROM voters GROUP BY party")
party_breakdown = c.fetchall()

conn.close()

print('=' * 60)
print(f'DATABASE SYNCHRONIZATION COMPLETE!')
print(f'Matched existing voters with real photos: {matched_count}')
print(f'Added new GP voters with English names:   {added_count}')
print(f'Total voters now in Database:            {total_voters}')
print(f'Party status breakdown:                  {[dict(r) for r in party_breakdown]}')
print('=' * 60)
