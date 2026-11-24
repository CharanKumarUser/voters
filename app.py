import os
import shutil
import sqlite3
import csv
import io
from flask import Flask, jsonify, request, send_from_directory, Response

app = Flask(__name__, static_folder='static')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_DB_PATH = os.path.join(BASE_DIR, 'voters.db')


def resolve_db_path():
    """Use a mounted Render Disk automatically if present (/var/data or /data),
    otherwise use the local voters.db on Render's disk / local workspace.
    No environment variables required."""
    for mount in ('/var/data', '/data'):
        if os.path.isdir(mount) and os.access(mount, os.W_OK):
            target = os.path.join(mount, 'voters.db')
            if not os.path.exists(target) and os.path.exists(SEED_DB_PATH):
                shutil.copy2(SEED_DB_PATH, target)
            return target, True
    return SEED_DB_PATH, False


DB_PATH, USING_MOUNTED_DISK = resolve_db_path()


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 30000')
    return conn


def init_db():
    """Enable WAL mode and indexes for instant concurrent reads/writes on disk."""
    conn = get_db()
    try:
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_voters_party ON voters(party)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_voters_gp ON voters(gp_serial)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_voters_voted ON voters(voted)')
        conn.commit()
    finally:
        conn.close()


init_db()


def compute_stats(conn):
    r = conn.execute('''
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN party = 'TDP' THEN 1 ELSE 0 END) AS tdp,
          SUM(CASE WHEN party IN ('YSRCP','YCP') THEN 1 ELSE 0 END) AS ycp,
          SUM(CASE WHEN party = 'NEUTRAL' THEN 1 ELSE 0 END) AS neutral,
          SUM(CASE WHEN party = 'DEAD' THEN 1 ELSE 0 END) AS dead,
          SUM(CASE WHEN party = 'UNKNOWN' THEN 1 ELSE 0 END) AS unknown,
          SUM(CASE WHEN party = 'UNASSIGNED' THEN 1 ELSE 0 END) AS unassigned,
          SUM(CASE WHEN voted = 1 THEN 1 ELSE 0 END) AS voted_total,
          SUM(CASE WHEN voted = 1 AND party = 'TDP' THEN 1 ELSE 0 END) AS voted_tdp,
          SUM(CASE WHEN voted = 1 AND party IN ('YSRCP','YCP') THEN 1 ELSE 0 END) AS voted_ycp,
          SUM(CASE WHEN voted = 1 AND party = 'NEUTRAL' THEN 1 ELSE 0 END) AS voted_neutral,
          SUM(CASE WHEN voted = 1 AND party = 'DEAD' THEN 1 ELSE 0 END) AS voted_dead,
          SUM(CASE WHEN voted = 1 AND party = 'UNKNOWN' THEN 1 ELSE 0 END) AS voted_unknown
        FROM voters
    ''').fetchone()
    s = {k: int(r[k] or 0) for k in r.keys()} if r else {}
    total = s.get('total', 0)
    tdp, ycp = s.get('tdp', 0), s.get('ycp', 0)

    def pct(n):
        return round(n / total * 100, 1) if total > 0 else 0

    if tdp > ycp:
        lead_party, lead_margin = 'TDP', tdp - ycp
    elif ycp > tdp:
        lead_party, lead_margin = 'YCP', ycp - tdp
    else:
        lead_party, lead_margin = 'TIE', 0

    return {
        'total': total,
        'marked': tdp + ycp + s.get('neutral', 0) + s.get('dead', 0) + s.get('unknown', 0),
        'unassigned': s.get('unassigned', 0),
        'tdp': tdp, 'tdp_pct': pct(tdp),
        'ycp': ycp, 'ysrcp': ycp, 'ycp_pct': pct(ycp),
        'neutral': s.get('neutral', 0), 'neutral_pct': pct(s.get('neutral', 0)),
        'dead': s.get('dead', 0), 'dead_pct': pct(s.get('dead', 0)),
        'unknown': s.get('unknown', 0), 'unknown_pct': pct(s.get('unknown', 0)),
        'unassigned_pct': pct(s.get('unassigned', 0)),
        'voted_total': s.get('voted_total', 0),
        'voted_tdp': s.get('voted_tdp', 0),
        'voted_ycp': s.get('voted_ycp', 0),
        'voted_neutral': s.get('voted_neutral', 0),
        'voted_dead': s.get('voted_dead', 0),
        'voted_unknown': s.get('voted_unknown', 0),
        'lead_party': lead_party,
        'lead_margin': lead_margin,
    }


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/api/health')
def health():
    return jsonify({
        'ok': True,
        'storage': 'sqlite (render persistent disk)' if USING_MOUNTED_DISK else 'sqlite (render disk)',
        'db_path': DB_PATH,
        'persistent': True,
    })


@app.route('/api/stats')
def get_stats():
    conn = get_db()
    try:
        return jsonify(compute_stats(conn))
    finally:
        conn.close()


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
    try:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
        return jsonify({'voters': rows, 'count': len(rows)})
    finally:
        conn.close()


@app.route('/api/sync')
def sync_state():
    """Single lightweight endpoint returning both voter marks and stats."""
    conn = get_db()
    try:
        rows = conn.execute('SELECT id, party, voted FROM voters').fetchall()
        stats = compute_stats(conn)
        return jsonify({
            'state': [[r['id'], r['party'], int(r['voted'] or 0)] for r in rows],
            'stats': stats,
        })
    finally:
        conn.close()


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
    try:
        conn.execute('UPDATE voters SET party = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_party, vid))
        conn.commit()
        row = conn.execute('SELECT * FROM voters WHERE id = ?', (vid,)).fetchone()
        if not row:
            return jsonify({'error': 'Voter not found'}), 404
        return jsonify({'success': True, 'voter': dict(row), 'stats': compute_stats(conn)})
    finally:
        conn.close()


@app.route('/api/voters/<int:vid>/voted', methods=['POST'])
def toggle_voted(vid):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    try:
        if 'voted' in data:
            conn.execute('UPDATE voters SET voted = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                         (1 if data.get('voted') else 0, vid))
        else:
            conn.execute('UPDATE voters SET voted = CASE WHEN voted = 1 THEN 0 ELSE 1 END, '
                         'updated_at = CURRENT_TIMESTAMP WHERE id = ?', (vid,))
        conn.commit()
        row = conn.execute('SELECT * FROM voters WHERE id = ?', (vid,)).fetchone()
        if not row:
            return jsonify({'error': 'Voter not found'}), 404
        return jsonify({'success': True, 'voter': dict(row), 'stats': compute_stats(conn)})
    finally:
        conn.close()


@app.route('/api/reset_counts', methods=['POST'])
def reset_counts():
    conn = get_db()
    try:
        conn.execute("UPDATE voters SET party = 'UNASSIGNED', voted = 0, updated_at = CURRENT_TIMESTAMP")
        conn.commit()
        stats = compute_stats(conn)
        return jsonify({
            'success': True,
            'stats': stats,
            'message': f"All voter counts and votes reset back to unassigned/0 for all {stats['total']} voters."
        })
    finally:
        conn.close()


@app.route('/api/sections')
def get_sections():
    conn = get_db()
    try:
        rows = conn.execute("SELECT DISTINCT section_name FROM voters WHERE section_name <> '' ORDER BY section_name").fetchall()
        return jsonify({'sections': [r['section_name'] for r in rows]})
    finally:
        conn.close()


@app.route('/api/export')
def export_csv():
    conn = get_db()
    try:
        rows = conn.execute('''
            SELECT gp_serial, serial_no, epic_id, name, relation_type, relation_name, house_no, age, gender,
                   section_name, party, voted
            FROM voters ORDER BY gp_serial ASC
        ''').fetchall()
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['GP Serial', 'Assembly Serial', 'EPIC ID', 'Name', 'Relation Type', 'Guardian Name',
                     'House No', 'Age', 'Gender', 'Section / Ward', 'Party Status', 'Voted / Polled'])
    for r in rows:
        writer.writerow([r['gp_serial'], r['serial_no'] or '', r['epic_id'], r['name'], r['relation_type'],
                         r['relation_name'], r['house_no'], r['age'], r['gender'], r['section_name'],
                         r['party'], 'YES' if r['voted'] == 1 else 'NO'])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=Kuppam_Cheekatipalle_GP_Voter_Tally.csv'}
    )


if __name__ == '__main__':
    print(f'Starting Voter Tally Server on http://localhost:5000  (DB: {DB_PATH})')
    app.run(host='0.0.0.0', port=5000, debug=False)
