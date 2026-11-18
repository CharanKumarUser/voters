import sqlite3

# Verified ground truth from direct inspection of all 84 official cards in voters-new.pdf
verified_cards = {
    1: {'name': 'Shriramulu', 'relation_type': 'Father', 'relation_name': 'Kasturappa', 'house_no': '1-1', 'gender': 'Male', 'epic_id': 'UXN0229948'},
    2: {'name': 'Madhu', 'relation_type': 'Husband', 'relation_name': 'Shriramulu', 'house_no': '1-1', 'gender': 'Female', 'epic_id': 'UXN0349274'},
    5: {'name': 'Balaji L', 'relation_type': 'Father', 'relation_name': 'Lakshmipati', 'house_no': '1-1/A1', 'gender': 'Male', 'epic_id': 'UXN2237550'},
    13: {'name': 'J Vijay', 'relation_type': 'Father', 'relation_name': 'Jayaram', 'house_no': '1-9', 'gender': 'Male', 'epic_id': 'UXN0618033'},
    24: {'name': 'Ishwaramma', 'relation_type': 'Husband', 'relation_name': 'Chinna Achari', 'house_no': '4-3/1', 'gender': 'Female', 'epic_id': 'UXN1794304'},
    35: {'name': 'N Navya', 'relation_type': 'Father', 'relation_name': 'N G Jagannadh Babu', 'house_no': '1-23', 'gender': 'Female', 'epic_id': 'UXN1101377'},
    71: {'name': 'K V Madhan Mohan', 'relation_type': 'Father', 'relation_name': 'Venkatappa', 'house_no': '4-2-1', 'gender': 'Male', 'epic_id': 'CWB1621713'},
    72: {'name': 'Mallika', 'relation_type': 'Husband', 'relation_name': 'K V Madhan Mohan', 'house_no': '4-2-1', 'gender': 'Female', 'epic_id': 'CWB1621721'},
    76: {'name': 'Ratnamma', 'relation_type': 'Husband', 'relation_name': 'Narayana', 'house_no': '4-11', 'gender': 'Female', 'epic_id': 'UXN0121608'},
    82: {'name': 'Venkatesu', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '4-11/1', 'gender': 'Male', 'epic_id': 'UXN0011932'},
    95: {'name': 'Radhappa Naidu', 'relation_type': 'Father', 'relation_name': 'Lakshmappa Naidu', 'house_no': '4-19', 'gender': 'Male', 'epic_id': 'UXN1794866'},
    127: {'name': 'Uday Kumar', 'relation_type': 'Father', 'relation_name': 'Shyam', 'house_no': '1-62', 'gender': 'Male', 'epic_id': 'UXN1142561'},
    130: {'name': 'Chandan Kumar M K', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '1-66', 'gender': 'Male', 'epic_id': 'UXN2410256'},
    132: {'name': 'M Raj Kumar M', 'relation_type': 'Father', 'relation_name': 'Ravvappa', 'house_no': '1-68', 'gender': 'Male', 'epic_id': 'UXN1022805'},
    135: {'name': 'C Bhavani', 'relation_type': 'Father', 'relation_name': 'M Chandrappa', 'house_no': '1-69', 'gender': 'Female', 'epic_id': 'UXN2077998'},
    138: {'name': 'Varalakshmi R', 'relation_type': 'Husband', 'relation_name': 'Raj Kumar', 'house_no': '1-70', 'gender': 'Female', 'epic_id': 'UXN1022813'},
    141: {'name': 'Lakshmamma', 'relation_type': 'Husband', 'relation_name': 'Muneppa', 'house_no': '1-72', 'gender': 'Female', 'epic_id': 'UXN1794023'},
    180: {'name': 'Geetha', 'relation_type': 'Husband', 'relation_name': 'Vijay Kumar', 'house_no': '1-85', 'gender': 'Female', 'epic_id': 'UXN0744137'},
    186: {'name': 'M S Vanitha', 'relation_type': 'Father', 'relation_name': 'M Subramanyam', 'house_no': '1-90', 'gender': 'Female', 'epic_id': 'UXN0805210'},
    187: {'name': 'N Sachin', 'relation_type': 'Father', 'relation_name': 'Nagabhushanam', 'house_no': '1-93', 'gender': 'Male', 'epic_id': 'UXN1185024'},
    198: {'name': 'Shanthi M', 'relation_type': 'Husband', 'relation_name': 'Anumappa L', 'house_no': '1-97', 'gender': 'Female', 'epic_id': 'UXN0997785'},
    211: {'name': 'K Pavithra', 'relation_type': 'Father', 'relation_name': 'K Krishnappa', 'house_no': '1-99', 'gender': 'Female', 'epic_id': 'UXN0661314'},
    226: {'name': 'G Naveena', 'relation_type': 'Father', 'relation_name': 'Govindappa', 'house_no': '2-12', 'gender': 'Female', 'epic_id': 'UXN2077899'},
    227: {'name': 'Muniswamy', 'relation_type': 'Father', 'relation_name': 'Muneppa', 'house_no': '2-49', 'gender': 'Male', 'epic_id': 'UXN1181486'},
    228: {'name': 'V Sundaramma', 'relation_type': 'Husband', 'relation_name': 'Simon', 'house_no': '2-67', 'gender': 'Female', 'epic_id': 'UXN1101419'},
    233: {'name': 'Munemma', 'relation_type': 'Husband', 'relation_name': 'Venkatesu', 'house_no': '4-11', 'gender': 'Female', 'epic_id': 'UXN1794700'},
    234: {'name': 'Chinnamma', 'relation_type': 'Husband', 'relation_name': 'Rajappa Naidu', 'house_no': '4-15/1', 'gender': 'Female', 'epic_id': 'UXN1794817'},
    235: {'name': 'Roja', 'relation_type': 'Husband', 'relation_name': 'Raj Kumar', 'house_no': '4-15/2', 'gender': 'Female', 'epic_id': 'UXN0617894'},
    237: {'name': 'Rukminamma', 'relation_type': 'Husband', 'relation_name': 'Ramakrishnappa', 'house_no': '4-20', 'gender': 'Female', 'epic_id': 'UXN1794882'},
    248: {'name': 'S Nirmala', 'relation_type': 'Husband', 'relation_name': 'S Gopal', 'house_no': '4-26', 'gender': 'Female', 'epic_id': 'UXN1101344'},
    255: {'name': 'Chinnapayappa', 'relation_type': 'Father', 'relation_name': 'Mugappa', 'house_no': '4-27', 'gender': 'Male', 'epic_id': 'CWB1621994'},
    282: {'name': 'T. Yugendra', 'relation_type': 'Father', 'relation_name': 'Chinna Thimmarayappa', 'house_no': '4-33/1', 'gender': 'Male', 'epic_id': 'UXN0139782'},
    300: {'name': 'C. Subramanyam', 'relation_type': 'Father', 'relation_name': 'Betappa', 'house_no': '4-35', 'gender': 'Male', 'epic_id': 'UXN0121632'},
    311: {'name': 'Anandappa C', 'relation_type': 'Father', 'relation_name': 'Chinna Munigowdu', 'house_no': '4-37', 'gender': 'Male', 'epic_id': 'UXN0011882'},
    335: {'name': 'K Chandana', 'relation_type': 'Father', 'relation_name': 'Krishna Murthy K', 'house_no': '4-40', 'gender': 'Female', 'epic_id': 'UXN1061373'},
    341: {'name': 'Prameelamma', 'relation_type': 'Husband', 'relation_name': 'Venkatapathi', 'house_no': '4-46', 'gender': 'Female', 'epic_id': 'UXN1795343'},
    344: {'name': 'Ayyappa', 'relation_type': 'Father', 'relation_name': 'Venkatapathi', 'house_no': '4-46', 'gender': 'Male', 'epic_id': 'UXN1181411'},
    345: {'name': 'V Kiran', 'relation_type': 'Father', 'relation_name': 'Venkatapathi', 'house_no': '4-46', 'gender': 'Male', 'epic_id': 'UXN1157718'},
    357: {'name': 'Bhagyamma', 'relation_type': 'Husband', 'relation_name': 'Ravichandra', 'house_no': '4-48', 'gender': 'Female', 'epic_id': 'CWB1621986'},
    377: {'name': 'Bellamma', 'relation_type': 'Husband', 'relation_name': 'Gullarappa', 'house_no': '4-52/1', 'gender': 'Female', 'epic_id': 'UXN1795467'},
    403: {'name': 'Yashodhamma', 'relation_type': 'Husband', 'relation_name': 'Nagaraju', 'house_no': '4-55/2', 'gender': 'Female', 'epic_id': 'UXN1795558'},
    404: {'name': 'Thimmakka', 'relation_type': 'Husband', 'relation_name': 'Venkatappa', 'house_no': '4-56', 'gender': 'Female', 'epic_id': 'UXN1795582'},
    412: {'name': 'Manjula', 'relation_type': 'Husband', 'relation_name': 'A. Ganesh', 'house_no': '4-57', 'gender': 'Female', 'epic_id': 'UXN0121517'},
    415: {'name': 'A. Babu', 'relation_type': 'Father', 'relation_name': 'Bhooseppa', 'house_no': '4-57', 'gender': 'Male', 'epic_id': 'UXN0121509'},
    418: {'name': 'A N Mahendra', 'relation_type': 'Father', 'relation_name': 'A Narayana', 'house_no': '4-57/1', 'gender': 'Male', 'epic_id': 'UXN1061324'},
    421: {'name': 'Thipparayappa', 'relation_type': 'Father', 'relation_name': 'Sonnappa', 'house_no': '4-57/2', 'gender': 'Male', 'epic_id': 'CWB2288157'},
    422: {'name': 'Hanumanthamma', 'relation_type': 'Husband', 'relation_name': 'S. Thimmarayappa', 'house_no': '4-57/2', 'gender': 'Female', 'epic_id': 'UXN0121541'},
    427: {'name': 'Munemma', 'relation_type': 'Husband', 'relation_name': 'Rangappa', 'house_no': '4-61', 'gender': 'Female', 'epic_id': 'UXN1795673'},
    428: {'name': 'Venkatesh', 'relation_type': 'Father', 'relation_name': 'Rangappa', 'house_no': '4-61', 'gender': 'Male', 'epic_id': 'UXN1795681'},
    430: {'name': 'Yallappa', 'relation_type': 'Father', 'relation_name': 'Rangappa', 'house_no': '4-61', 'gender': 'Male', 'epic_id': 'CWB2288330'},
    432: {'name': 'Lakshmipathi', 'relation_type': 'Father', 'relation_name': 'Rangappa', 'house_no': '4-61', 'gender': 'Male', 'epic_id': 'UXN0121558'},
    436: {'name': 'Ranjith Kumar R', 'relation_type': 'Father', 'relation_name': 'Ramesh M', 'house_no': '4-61-A', 'gender': 'Male', 'epic_id': 'UXN2250934'},
    437: {'name': 'Harathi R', 'relation_type': 'Father', 'relation_name': 'Ramesh M', 'house_no': '4-61-A', 'gender': 'Female', 'epic_id': 'UXN2237543'},
    442: {'name': 'Yellamma', 'relation_type': 'Husband', 'relation_name': 'Gullappa', 'house_no': '4-62', 'gender': 'Female', 'epic_id': 'UXN1795699'},
    445: {'name': 'V Manjunath', 'relation_type': 'Father', 'relation_name': 'Venkatesh V', 'house_no': '4-62', 'gender': 'Male', 'epic_id': 'UXN1061118'},
    448: {'name': 'M Suresh', 'relation_type': 'Father', 'relation_name': 'M Munaswamy', 'house_no': '4-68', 'gender': 'Male', 'epic_id': 'UXN1061225'},
    451: {'name': 'Chinnapayappa', 'relation_type': 'Father', 'relation_name': 'Munirathnam', 'house_no': '4-72', 'gender': 'Male', 'epic_id': 'UXN1796093'},
    454: {'name': 'Chandramma', 'relation_type': 'Husband', 'relation_name': 'Shankarappa', 'house_no': '4-72', 'gender': 'Female', 'epic_id': 'UXN0213728'},
    457: {'name': 'E. Chinnappa', 'relation_type': 'Father', 'relation_name': 'Abbayappa', 'house_no': '4-73/1', 'gender': 'Male', 'epic_id': 'UXN1795764'},
    460: {'name': 'Venkatesh', 'relation_type': 'Father', 'relation_name': 'Chinnasamappa', 'house_no': '4-73/1', 'gender': 'Male', 'epic_id': 'CWB2835882'},
    461: {'name': 'Balakrishna', 'relation_type': 'Father', 'relation_name': 'E. Chinnappa', 'house_no': '4-73/1', 'gender': 'Male', 'epic_id': 'UXN1795749'},
    463: {'name': 'A C Thimmarayappa', 'relation_type': 'Father', 'relation_name': 'E Chinnappa', 'house_no': '4-73/1', 'gender': 'Male', 'epic_id': 'UXN0012161'},
    464: {'name': 'Padmamma', 'relation_type': 'Husband', 'relation_name': 'E. Venkatesh', 'house_no': '4-73/1', 'gender': 'Female', 'epic_id': 'CWB2288215'},
    465: {'name': 'E Chandramma', 'relation_type': 'Husband', 'relation_name': 'Ramesh', 'house_no': '4-73/1', 'gender': 'Female', 'epic_id': 'UXN0012153'},
    495: {'name': 'K Sandhya', 'relation_type': 'Father', 'relation_name': 'C Krishna Murthy', 'house_no': 'MESTRINAYANURU', 'gender': 'Female', 'epic_id': 'UXN1101401'},
    496: {'name': 'C Valli', 'relation_type': 'Husband', 'relation_name': 'C Chinnadorai', 'house_no': 'SEETHAM CHENU', 'gender': 'Female', 'epic_id': 'UXN1101393'},
    497: {'name': 'S Jeevanandana', 'relation_type': 'Father', 'relation_name': 'A Shankar', 'house_no': 'SEETHAM CHENU', 'gender': 'Male', 'epic_id': 'UXN1101385'},
    526: {'name': 'Gurrappa', 'relation_type': 'Father', 'relation_name': 'Muneppa', 'house_no': '4-64/1', 'gender': 'Male', 'epic_id': 'UXN1795871'},
    556: {'name': 'T Thimmaraju', 'relation_type': 'Father', 'relation_name': 'Thimmarayappa', 'house_no': '4-68', 'gender': 'Male', 'epic_id': 'UXN0012138'},
    566: {'name': 'Muneppa', 'relation_type': 'Father', 'relation_name': 'Donneppa', 'house_no': '4-70', 'gender': 'Male', 'epic_id': 'UXN1796044'},
    580: {'name': 'Narayanamma', 'relation_type': 'Husband', 'relation_name': 'Venkatesu', 'house_no': '1-2', 'gender': 'Female', 'epic_id': 'UXN1178441'},
    581: {'name': 'Ramachandra', 'relation_type': 'Father', 'relation_name': 'Venkatesh', 'house_no': '1-98', 'gender': 'Male', 'epic_id': 'UXN1143734'},
    582: {'name': 'V Venkatachalam', 'relation_type': 'Father', 'relation_name': 'Venkatesh', 'house_no': '1-98', 'gender': 'Male', 'epic_id': 'UXN2054427'},
    583: {'name': 'R Hemalatha', 'relation_type': 'Husband', 'relation_name': 'B Naveen', 'house_no': '2-11', 'gender': 'Female', 'epic_id': 'UXN2087559'},
    584: {'name': 'R Soma Shekar', 'relation_type': 'Father', 'relation_name': 'B Ramappa', 'house_no': '2-43', 'gender': 'Male', 'epic_id': 'UXN2089712'},
    585: {'name': 'V Ashwath', 'relation_type': 'Father', 'relation_name': 'Venkataramanappa', 'house_no': '2-45', 'gender': 'Male', 'epic_id': 'UXN2054443'},
    586: {'name': 'Rajeshwari', 'relation_type': 'Husband', 'relation_name': 'Kadirappa', 'house_no': '2-74', 'gender': 'Female', 'epic_id': 'UXN2085611'},
    587: {'name': 'S Amaraveni', 'relation_type': 'Husband', 'relation_name': 'M Venkatachalam', 'house_no': '2-77', 'gender': 'Female', 'epic_id': 'UXN2054419'},
    588: {'name': 'M Swapna', 'relation_type': 'Husband', 'relation_name': 'V Govindarajulu', 'house_no': '2-587', 'gender': 'Female', 'epic_id': 'UXN2345783'},
    589: {'name': 'G Sunitha', 'relation_type': 'Husband', 'relation_name': 'R Krishna Murthy', 'house_no': '3-15', 'gender': 'Female', 'epic_id': 'UXN2085629'},
    590: {'name': 'N Murugesha', 'relation_type': 'Father', 'relation_name': 'Narayanappa', 'house_no': '3-32', 'gender': 'Male', 'epic_id': 'UXN1064757'},
    591: {'name': 'E Mahendra', 'relation_type': 'Father', 'relation_name': 'Mopurappa', 'house_no': '3-34', 'gender': 'Male', 'epic_id': 'UXN1177781'},
    592: {'name': 'Munichandra', 'relation_type': 'Father', 'relation_name': 'Mallappa', 'house_no': '3-38', 'gender': 'Male', 'epic_id': 'UXN2166791'},
    593: {'name': 'Shakuntala', 'relation_type': 'Mother', 'relation_name': 'Subramanyam', 'house_no': '3-68', 'gender': 'Female', 'epic_id': 'UXN0905747'}
}

conn = sqlite3.connect('voters.db')
c = conn.cursor()

updated_count = 0
for gp_s, info in verified_cards.items():
    c.execute('''
        UPDATE voters SET
            name = ?,
            relation_type = ?,
            relation_name = ?,
            house_no = ?,
            gender = ?,
            epic_id = ?,
            photo_path = ?,
            crop_path = ?
        WHERE gp_serial = ?
    ''', (
        info['name'],
        info['relation_type'],
        info['relation_name'],
        info['house_no'],
        info['gender'],
        info['epic_id'],
        f"/static/photos/photo_gp_{gp_s:04d}.jpg",
        f"/static/crops/card_gp_{gp_s:04d}.jpg",
        gp_s
    ))
    updated_count += 1

conn.commit()
print(f"Successfully updated {updated_count} cards with verified ground truth!")

# Check specific cards reported by user
c.execute("SELECT gp_serial, epic_id, name, relation_type, relation_name, gender, house_no FROM voters WHERE gp_serial IN (130, 135, 180, 186, 187, 222)")
for r in c.fetchall():
    print(" ", r)

conn.close()
