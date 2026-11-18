import sqlite3
import re

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT gp_serial, epic_id, name, relation_type, relation_name, gender, house_no FROM voters ORDER BY gp_serial ASC")
rows = c.fetchall()

print(f"Auditing all {len(rows)} voters in voters.db for gender and relation consistency...")

issues = []

female_keywords = ['AMMA', 'DEVI', 'LATHA', 'KUMARI', 'BAI', 'BHAGYA', 'RADHA', 'SHOBHA', 'PARVATHI', 'LAKSHMI', 'SARASWATHI', 'GOWRI', 'RANI', 'PUSHPA', 'VANI', 'ROOPA', 'SHILPA', 'CHANDRAKALA', 'MAMATHA', 'SWATHI', 'SUJATHA', 'KAVITHA', 'BHAVANI', 'PADMA', 'ANITHA', 'GEETHA', 'SOWMYA', 'CHANDRAMMA', 'VENKATAMMA', 'CHINNAMMA', 'GOWRAMMA', 'MUNEMMA', 'MANGAMMA', 'NAGARATHNA', 'VARALAKSHMI', 'SHYAMALA', 'MANJULA', 'ASHA', 'REKHA', 'DIVYA', 'POOJA', 'PRIYA', 'USHA', 'SUNITHA', 'MEENA', 'DEEPIKA', 'LAVANYA', 'LEELAVATHI', 'SARALAMMA', 'DHANALAKSHMI', 'SUGUNA', 'MALATHI', 'SOUJANYA', 'SHAKUNTALA', 'MALLIKA', 'RATNAMMA', 'MADHU', 'PADMAMMA', 'RATHNAMMA', 'JAYAMMA', 'PUSHAPALATHA', 'KRISHNAMMA', 'BHUVANESHWARI', 'HEMAVATHI', 'ISHWARAMMA', 'NAVYA', 'SHANTHI', 'PAVITHRA', 'NAVEENA', 'SUNDARAMMA', 'CHINNAMMA', 'ROJA', 'RUKMINAMMA', 'NIRMALA', 'CHANDANA', 'PRAMEELAMMA', 'YASHODHAMMA', 'THIMMAKKA', 'HANUMANTHAMMA', 'HARATHI', 'YELLAMMA', 'CHANDRAMMA', 'SANDHYA', 'VALLI', 'NARAYANAMMA', 'HEMALATHA', 'RAJESHWARI', 'AMARAVENI', 'SWAPNA']
male_keywords = ['KUMAR', 'APPA', 'RAJU', 'REDDY', 'NAIDU', 'GOWD', 'CHARI', 'SWAMY', 'PRASAD', 'BABU', 'VARMA', 'MURTHY', 'RAMAN', 'RAMA', 'MOHAN', 'SHANKAR', 'SHEKAR', 'VENKATESH', 'KRISHNA', 'NAIK', 'IAH', 'AIAH', 'SACHIN', 'AYYAPPA', 'KIRAN', 'GURRAPPA', 'MUNEPPA', 'ASHWATH', 'MAHENDRA', 'MUNICHANDRA', 'MURUGESHA', 'YUGENDRA', 'SUBRAMANYAM', 'ANANDAPPA', 'THIPPARAYAPPA', 'YALLAPPA', 'LAKSHMIPATHI', 'BALAKRISHNA', 'THIMMARAYAPPA']

for r in rows:
    gp_s = r['gp_serial']
    name = r['name'].upper()
    g = r['gender']
    rel = r['relation_type']

    # If relation is Husband, voter must be Female
    if rel == 'Husband' and g != 'Female':
        issues.append((gp_s, r['name'], g, 'Husband relation but marked Male'))
    # If relation is Wife, voter must be Male
    if rel == 'Wife' and g != 'Male':
        issues.append((gp_s, r['name'], g, 'Wife relation but marked Female'))

    # Check clear female name but marked Male
    is_f_name = any(re.search(r'\b' + k + r'\b|' + k + r'$', name) for k in female_keywords)
    is_m_name = any(re.search(r'\b' + k + r'\b|' + k + r'$', name) for k in male_keywords)

    if is_f_name and not is_m_name and g == 'Male':
        issues.append((gp_s, r['name'], g, 'Female name marked Male'))
    elif is_m_name and not is_f_name and g == 'Female':
        issues.append((gp_s, r['name'], g, 'Male name marked Female'))

print(f"Total potential issues detected: {len(issues)}")
for iss in issues:
    print(" ", iss)

conn.close()
