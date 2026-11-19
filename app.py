import os
import sqlite3
import csv
import io
import datetime
from flask import Flask, jsonify, request, send_from_directory, Response

app = Flask(__name__, static_folder='static')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, 'voters.db')   # local DB / seed data source

# ---------------------------------------------------------------------------
# STORAGE BACKEND
# Render (free plan) has an EPHEMERAL disk: any change written to voters.db is
# wiped whenever the service sleeps, restarts or redeploys. To keep marks
# permanently we use an external PostgreSQL database when DATABASE_URL is set.
# Locally (no DATABASE_URL) we keep using the SQLite file.
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = 'postgresql://' + DATABASE_URL[len('postgres://'):]
USE_PG = DATABASE_URL.startswith('postgresql://')

if USE_PG:
    import psycopg2
    import psycopg2.extras

COLUMNS = ['id', 'serial_no', 'epic_id', 'name', 'relation_type', 'relation_name', 'house_no',
           'age', 'gender', 'section_no', 'section_name', 'ac_name', 'part_no', 'page_no',
           'crop_path', 'party', 'voted', 'notes', 'ocr_done', 'updated_at', 'photo_path', 'gp_serial']

PG_SCHEMA = '''
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY,
    serial_no INTEGER UNIQUE,
    epic_id TEXT DEFAULT '',
    name TEXT DEFAULT '',
    relation_type TEXT DEFAULT 'Father',
    relation_name TEXT DEFAULT '',
    house_no TEXT DEFAULT '',
    age INTEGER DEFAULT 0,
    gender TEXT DEFAULT 'Male',
    section_no TEXT DEFAULT '',
    section_name TEXT DEFAULT '',
    ac_name TEXT DEFAULT '175-KUPPAM',
    part_no TEXT DEFAULT '159',
    page_no INTEGER,
    crop_path TEXT,
    party TEXT DEFAULT 'UNASSIGNED',
    voted INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    ocr_done INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    photo_path TEXT,
    gp_serial INTEGER
);
CREATE INDEX IF NOT EXISTS idx_voters_party ON voters(party);
CREATE INDEX IF NOT EXISTS idx_voters_gp ON voters(gp_serial);
'''


def get_conn():
    if USE_PG:
        return psycopg2.connect(DATABASE_URL, connect_timeout=15)
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _sql(query):
    """Convert SQLite-style SQL to the active backend's dialect."""
    if USE_PG:
        return query.replace('?', '%s').replace(' LIKE ', ' ILIKE ')
    return query


def _clean(row):
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            d[k] = v.strftime('%Y-%m-%d %H:%M:%S')
    return d


def query_all(query, params=()):
    conn = get_conn()
    try:
        if USE_PG:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = conn.cursor()
        cur.execute(_sql(query), params)
        return [_clean(r) for r in cur.fetchall()]
    finally:
        conn.close()


def query_one(query, params=()):
    rows = query_all(query, params)
    return rows[0] if rows else None


def execute(query, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_sql(query), params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def init_db():
    """Create the Postgres table and seed it ONCE from the bundled voters.db.
    Existing data is never overwritten, so marks survive restarts/redeploys."""
    if not USE_PG:
        return
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(PG_SCHEMA)
        conn.commit()
        cur.execute('SELECT COUNT(*) FROM voters')
        if cur.fetchone()[0] > 0:
            return
        src = sqlite3.connect(SQLITE_PATH)
        src.row_factory = sqlite3.Row
        rows = src.execute('SELECT * FROM voters ORDER BY id').fetchall()
        src.close()
        values = []
        for r in rows:
            d = dict(r)
            d['party'] = 'UNASSIGNED'   # start with clean counts
            d['voted'] = 0
            d['updated_at'] = None
            values.append(tuple(d.get(c) for c in COLUMNS))
        psycopg2.extras.execute_values(
            cur,
            f'INSERT INTO voters ({", ".join(COLUMNS)}) VALUES %s ON CONFLICT (id) DO NOTHING',
            values)
        cur.execute('UPDATE voters SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL')
        conn.commit()
        print(f'[init_db] Seeded PostgreSQL with {len(values)} voters')
    finally:
        conn.close()


init_db()


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------
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
        'storage': 'postgresql (persistent)' if USE_PG else 'sqlite (local file)',
        'persistent': USE_PG or not os.environ.get('RENDER'),
    })


@app.route('/api/stats')
def get_stats():
    r = query_one('''
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
    ''') or {}
    s = {k: int(v or 0) for k, v in r.items()}
    total = s.get('total', 0)
    tdp, ycp = s['tdp'], s['ycp']

    def pct(n):
        return round(n / total * 100, 1) if total > 0 else 0

    if tdp > ycp:
        lead_party, lead_margin = 'TDP', tdp - ycp
    elif ycp > tdp:
        lead_party, lead_margin = 'YCP', ycp - tdp
    else:
        lead_party, lead_margin = 'TIE', 0

    return jsonify({
        'total': total,
        'marked': tdp + ycp + s['neutral'] + s['dead'] + s['unknown'],
        'unassigned': s['unassigned'],
        'tdp': tdp, 'tdp_pct': pct(tdp),
        'ycp': ycp, 'ysrcp': ycp, 'ycp_pct': pct(ycp),
        'neutral': s['neutral'], 'neutral_pct': pct(s['neutral']),
        'dead': s['dead'], 'dead_pct': pct(s['dead']),
        'unknown': s['unknown'], 'unknown_pct': pct(s['unknown']),
        'unassigned_pct': pct(s['unassigned']),
        'voted_total': s['voted_total'],
        'voted_tdp': s['voted_tdp'],
        'voted_ycp': s['voted_ycp'],
        'voted_neutral': s['voted_neutral'],
        'voted_dead': s['voted_dead'],
        'voted_unknown': s['voted_unknown'],
        'lead_party': lead_party,
        'lead_margin': lead_margin,
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

    rows = query_all(query, params)
    return jsonify({'voters': rows, 'count': len(rows)})


@app.route('/api/sync')
def sync_state():
    """Lightweight snapshot of every voter's mark, polled by all open browsers
    so changes made by one person appear for everyone within seconds."""
    rows = query_all('SELECT id, party, voted FROM voters')
    return jsonify({'state': [[r['id'], r['party'], int(r['voted'] or 0)] for r in rows]})


@app.route('/api/voters/<int:vid>/party', methods=['POST'])
def update_party(vid):
    data = request.get_json(force=True, silent=True) or {}
    new_party = data.get('party') or request.form.get('party') or request.args.get('party', 'UNASSIGNED')
    new_party = str(new_party).upper()
    if new_party == 'YSRCP':
        new_party = 'YCP'
    if new_party not in ['TDP', 'YCP', 'NEUTRAL', 'DEAD', 'UNKNOWN', 'UNASSIGNED']:
        return jsonify({'error': 'Invalid status', 'received': new_party}), 400

    execute('UPDATE voters SET party = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_party, vid))
    updated = query_one('SELECT * FROM voters WHERE id = ?', (vid,))
    if not updated:
        return jsonify({'error': 'Voter not found'}), 404
    return jsonify({'success': True, 'voter': updated})


@app.route('/api/voters/<int:vid>/voted', methods=['POST'])
def toggle_voted(vid):
    data = request.get_json(force=True, silent=True) or {}
    if 'voted' in data:
        # Explicit value -> idempotent, safe when several people click at once
        execute('UPDATE voters SET voted = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (1 if data.get('voted') else 0, vid))
    else:
        execute('UPDATE voters SET voted = CASE WHEN voted = 1 THEN 0 ELSE 1 END, '
                'updated_at = CURRENT_TIMESTAMP WHERE id = ?', (vid,))
    updated = query_one('SELECT * FROM voters WHERE id = ?', (vid,))
    if not updated:
        return jsonify({'error': 'Voter not found'}), 404
    return jsonify({'success': True, 'voter': updated})


@app.route('/api/reset_counts', methods=['POST'])
def reset_counts():
    execute("UPDATE voters SET party = 'UNASSIGNED', voted = 0, updated_at = CURRENT_TIMESTAMP")
    total = query_one('SELECT COUNT(*) AS n FROM voters')['n']
    return jsonify({
        'success': True,
        'message': f'All voter counts and votes reset back to unassigned/0 for all {total} voters.'
    })


@app.route('/api/sections')
def get_sections():
    rows = query_all("SELECT DISTINCT section_name FROM voters WHERE section_name <> '' ORDER BY section_name")
    return jsonify({'sections': [r['section_name'] for r in rows]})


@app.route('/api/export')
def export_csv():
    rows = query_all('''
        SELECT gp_serial, serial_no, epic_id, name, relation_type, relation_name, house_no, age, gender,
               section_name, party, voted
        FROM voters ORDER BY gp_serial ASC
    ''')
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
    print(f'Starting Voter Tally Server on http://localhost:5000  (storage: {"PostgreSQL" if USE_PG else "SQLite"})')
    app.run(host='0.0.0.0', port=5000, debug=False)
