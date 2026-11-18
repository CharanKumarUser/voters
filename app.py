import os
import sqlite3
import csv
import io
from flask import Flask, jsonify, request, send_from_directory, Response

app = Flask(__name__, static_folder='static')
DB_PATH = 'voters.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/stats')
def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM voters')
    total = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE party = 'TDP'")
    tdp = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE party IN ('YSRCP', 'YCP')")
    ycp = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE party = 'NEUTRAL'")
    neutral = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE party = 'DEAD'")
    dead = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE party = 'UNKNOWN'")
    unknown = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE party = 'UNASSIGNED'")
    unassigned = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE voted = 1")
    voted_total = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE voted = 1 AND party = 'TDP'")
    voted_tdp = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE voted = 1 AND party IN ('YSRCP', 'YCP')")
    voted_ycp = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE voted = 1 AND party = 'NEUTRAL'")
    voted_neutral = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE voted = 1 AND party = 'DEAD'")
    voted_dead = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM voters WHERE voted = 1 AND party = 'UNKNOWN'")
    voted_unknown = c.fetchone()[0] or 0

    conn.close()

    marked = tdp + ycp + neutral + dead + unknown
    tdp_pct = round((tdp / total * 100), 1) if total > 0 else 0
    ycp_pct = round((ycp / total * 100), 1) if total > 0 else 0
    neutral_pct = round((neutral / total * 100), 1) if total > 0 else 0
    dead_pct = round((dead / total * 100), 1) if total > 0 else 0
    unknown_pct = round((unknown / total * 100), 1) if total > 0 else 0
    unassigned_pct = round((unassigned / total * 100), 1) if total > 0 else 0

    if tdp > ycp:
        lead_party = 'TDP'
        lead_margin = tdp - ycp
    elif ycp > tdp:
        lead_party = 'YCP'
        lead_margin = ycp - tdp
    else:
        lead_party = 'TIE'
        lead_margin = 0

    return jsonify({
        'total': total,
        'marked': marked,
        'unassigned': unassigned,
        'tdp': tdp,
        'tdp_pct': tdp_pct,
        'ycp': ycp,
        'ysrcp': ycp,
        'ycp_pct': ycp_pct,
        'neutral': neutral,
        'neutral_pct': neutral_pct,
        'dead': dead,
        'dead_pct': dead_pct,
        'unknown': unknown,
        'unknown_pct': unknown_pct,
        'unassigned_pct': unassigned_pct,
        'voted_total': voted_total,
        'voted_tdp': voted_tdp,
        'voted_ycp': voted_ycp,
        'voted_neutral': voted_neutral,
        'voted_dead': voted_dead,
        'voted_unknown': voted_unknown,
        'lead_party': lead_party,
        'lead_margin': lead_margin
    })

@app.route('/api/voters')
def get_voters():
    search = request.args.get('search', '').strip()
    party = request.args.get('party', 'ALL').upper()
    gender = request.args.get('gender', 'ALL')
    voted = request.args.get('voted', 'ALL')
    section = request.args.get('section', 'ALL')
    sort = request.args.get('sort', 'gp_serial_asc')

    query = 'SELECT * FROM voters WHERE 1=1'
    params = []

    if search:
        query += ''' AND (
            name LIKE ? OR 
            epic_id LIKE ? OR 
            relation_name LIKE ? OR 
            house_no LIKE ? OR 
            CAST(serial_no AS TEXT) = ? OR
            CAST(gp_serial AS TEXT) = ?
        )'''
        term = f'%{search}%'
        params.extend([term, term, term, term, search, search])

    if party in ['TDP', 'YSRCP', 'YCP', 'NEUTRAL', 'DEAD', 'UNKNOWN', 'UNASSIGNED', 'UNMARKED']:
        if party in ['YSRCP', 'YCP']:
            query += " AND party IN ('YSRCP', 'YCP')"
        elif party in ['UNASSIGNED', 'UNMARKED']:
            query += " AND party = 'UNASSIGNED'"
        else:
            query += ' AND party = ?'
            params.append(party)

    if gender in ['Male', 'Female']:
        query += ' AND gender = ?'
        params.append(gender)

    if voted in ['0', '1']:
        query += ' AND voted = ?'
        params.append(int(voted))

    if section != 'ALL' and section:
        query += ' AND section_name = ?'
        params.append(section)

    sort_orders = {
        'gp_serial_asc': 'gp_serial ASC, serial_no ASC',
        'gp_serial_desc': 'gp_serial DESC, serial_no DESC',
        'serial_asc': 'serial_no ASC',
        'serial_desc': 'serial_no DESC',
        'house_asc': 'house_no ASC, gp_serial ASC',
        'age_asc': 'age ASC, gp_serial ASC',
        'age_desc': 'age DESC, gp_serial ASC',
        'name_asc': 'name ASC'
    }
    query += f' ORDER BY {sort_orders.get(sort, "gp_serial ASC, serial_no ASC")}'

    conn = get_db()
    c = conn.cursor()
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    return jsonify({'voters': rows, 'count': len(rows)})

@app.route('/api/voters/<int:vid>/party', methods=['POST'])
def update_party(vid):
    data = request.get_json(force=True, silent=True) or {}
    new_party = data.get('party') or request.form.get('party') or request.args.get('party', 'UNASSIGNED')
    new_party = str(new_party).upper()
    if new_party == 'YSRCP':
        new_party = 'YCP'
    if new_party not in ['TDP', 'YCP', 'NEUTRAL', 'DEAD', 'UNKNOWN', 'UNASSIGNED']:
        return jsonify({'error': 'Invalid status', 'received': new_party}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE voters SET party = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_party, vid))
    conn.commit()
    c.execute('SELECT * FROM voters WHERE id = ?', (vid,))
    updated = dict(c.fetchone())
    conn.close()

    return jsonify({'success': True, 'voter': updated})

@app.route('/api/voters/<int:vid>/voted', methods=['POST'])
def toggle_voted(vid):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE voters SET voted = CASE WHEN voted = 1 THEN 0 ELSE 1 END, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (vid,))
    conn.commit()
    c.execute('SELECT * FROM voters WHERE id = ?', (vid,))
    updated = dict(c.fetchone())
    conn.close()

    return jsonify({'success': True, 'voter': updated})

@app.route('/api/reset_counts', methods=['POST'])
def reset_counts():
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE voters SET party = 'UNASSIGNED', voted = 0, updated_at = CURRENT_TIMESTAMP")
    conn.commit()
    c.execute("SELECT COUNT(*) FROM voters")
    total = c.fetchone()[0]
    conn.close()
    return jsonify({
        'success': True,
        'message': f'All voter counts and votes reset back to unassigned/0 for all {total} voters.'
    })

@app.route('/api/sections')
def get_sections():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT DISTINCT section_name FROM voters WHERE section_name != "" ORDER BY section_name')
    sections = [r[0] for r in c.fetchall()]
    conn.close()
    return jsonify({'sections': sections})

@app.route('/api/export')
def export_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT gp_serial, serial_no, epic_id, name, relation_type, relation_name, house_no, age, gender, section_name, party, voted
        FROM voters ORDER BY gp_serial ASC
    ''')
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['GP Serial', 'Assembly Serial', 'EPIC ID', 'Name', 'Relation Type', 'Guardian Name', 'House No', 'Age', 'Gender', 'Section / Ward', 'Party Status', 'Voted / Polled'])
    for r in rows:
        voted_str = 'YES' if r[11] == 1 else 'NO'
        writer.writerow([r[0], r[1] or '', r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], voted_str])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=Kuppam_Cheekatipalle_GP_Voter_Tally.csv'}
    )

if __name__ == '__main__':
    print('Starting Voter Tally Server on http://localhost:5000')
    app.run(host='0.0.0.0', port=5000, debug=False)
