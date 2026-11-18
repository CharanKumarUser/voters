import sqlite3
import re

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM voters')
rows = c.fetchall()

female_endings = ['AMMA', 'DEVI', 'KUMARI', 'LATHA', 'BHAGYA', 'RADHA', 'SHOBHA', 'PARVATHI', 'LAKSHMI', 'SARASWATHI', 'GOWRI', 'RANI', 'PUSHPA', 'VANI', 'ROOPA', 'MADHU', 'SHILPA', 'CHANDRAKALA', 'MAMATHA', 'SWATHI', 'SUJATHA', 'KAVITHA', 'BHAVANI', 'PADMA', 'SAROJ']
male_endings = ['APPA', 'RAJU', 'REDDY', 'NAIDU', 'GOWD', 'KUMAR', 'CHARI', 'SWAMY', 'PRASAD', 'BABU', 'VARMA', 'MURTHY', 'RAMAN', 'RAMA', 'MOHAN', 'SHANKAR', 'SHEKAR', 'VENKATESH', 'KRISHNA']

f_as_m = []
m_as_f = []

for r in rows:
    name = r['name'].upper()
    g = r['gender']
    
    # Check if female name marked as Male
    if g == 'Male' and any(re.search(r'\b' + ind + r'\b|' + ind + r'$', name) for ind in female_endings):
        # make sure not false positive like 'RAMA' in 'RAMAPPA'
        if not any(m in name for m in ['APPA', 'KUMAR', 'RAJU', 'BABU']):
            f_as_m.append(dict(r))

    # Check if male name marked as Female
    if g == 'Female' and any(re.search(r'\b' + ind + r'\b|' + ind + r'$', name) for ind in male_endings):
        if not any(f in name for f in ['AMMA', 'DEVI', 'LATHA', 'KUMARI']):
            m_as_f.append(dict(r))

print(f"Female names marked as Male in DB: {len(f_as_m)}")
for x in f_as_m[:10]:
    print(f"  ID:{x['id']} | GP#{x['gp_serial']} | Name:{x['name']} | Gender:{x['gender']} | Relation:{x['relation_type']} {x['relation_name']}")

print(f"\nMale names marked as Female in DB: {len(m_as_f)}")
for x in m_as_f[:10]:
    print(f"  ID:{x['id']} | GP#{x['gp_serial']} | Name:{x['name']} | Gender:{x['gender']} | Relation:{x['relation_type']} {x['relation_name']}")
