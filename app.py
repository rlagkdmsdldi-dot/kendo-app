from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kendo-wansan-secret-2024')
CORS(app)

DB_PATH = os.environ.get('DB_PATH', 'kendo.db')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'wansan1234')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT,
                place TEXT,
                fee_individual INTEGER DEFAULT 0,
                fee_team INTEGER DEFAULT 0,
                deadline TEXT,
                notices TEXT DEFAULT '[]',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                birth TEXT NOT NULL,
                rank TEXT NOT NULL,
                phone TEXT NOT NULL,
                event_type TEXT NOT NULL,
                fee INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
            )
        ''')
        conn.commit()

init_db()

# ── 페이지 라우트 ──────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ── 관리자 인증 ───────────────────────────────────────────

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': '비밀번호가 틀렸습니다'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({'ok': True})

@app.route('/api/admin/check')
def admin_check():
    return jsonify({'ok': session.get('admin', False)})

# ── 대회 API ──────────────────────────────────────────────

@app.route('/api/tournaments', methods=['GET'])
def get_tournaments():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM tournaments ORDER BY created_at DESC').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/tournaments/active', methods=['GET'])
def get_active_tournament():
    with get_db() as conn:
        row = conn.execute('SELECT * FROM tournaments WHERE active=1 ORDER BY created_at DESC LIMIT 1').fetchone()
    if not row:
        return jsonify(None)
    return jsonify(dict(row))

@app.route('/api/tournaments', methods=['POST'])
def create_tournament():
    if not session.get('admin'):
        return jsonify({'error': '권한 없음'}), 403
    data = request.json
    with get_db() as conn:
        conn.execute('UPDATE tournaments SET active=0')
        conn.execute('''
            INSERT INTO tournaments (name, date, place, fee_individual, fee_team, deadline, notices, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            data.get('name', ''),
            data.get('date', ''),
            data.get('place', ''),
            data.get('fee_individual', 0),
            data.get('fee_team', 0),
            data.get('deadline', ''),
            json.dumps(data.get('notices', []), ensure_ascii=False)
        ))
        conn.commit()
        tid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    return jsonify({'ok': True, 'id': tid})

@app.route('/api/tournaments/<int:tid>/activate', methods=['POST'])
def activate_tournament(tid):
    if not session.get('admin'):
        return jsonify({'error': '권한 없음'}), 403
    with get_db() as conn:
        conn.execute('UPDATE tournaments SET active=0')
        conn.execute('UPDATE tournaments SET active=1 WHERE id=?', (tid,))
        conn.commit()
    return jsonify({'ok': True})

# ── 신청 API ──────────────────────────────────────────────

@app.route('/api/registrations', methods=['POST'])
def create_registration():
    data = request.json
    required = ['tournament_id', 'name', 'birth', 'rank', 'phone', 'event_type']
    if not all(data.get(k) for k in required):
        return jsonify({'error': '필수 항목을 모두 입력해주세요'}), 400

    with get_db() as conn:
        t = conn.execute('SELECT * FROM tournaments WHERE id=?', (data['tournament_id'],)).fetchone()
        if not t:
            return jsonify({'error': '대회 정보를 찾을 수 없습니다'}), 404

        fee = 0
        et = data['event_type']
        if et == 'individual':
            fee = t['fee_individual']
        elif et == 'team':
            fee = t['fee_team']
        elif et == 'both':
            fee = t['fee_individual'] + t['fee_team']

        # 중복 신청 체크
        dup = conn.execute(
            'SELECT id FROM registrations WHERE tournament_id=? AND name=? AND birth=?',
            (data['tournament_id'], data['name'], data['birth'])
        ).fetchone()
        if dup:
            return jsonify({'error': '이미 신청하셨습니다'}), 409

        conn.execute('''
            INSERT INTO registrations (tournament_id, name, birth, rank, phone, event_type, fee)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['tournament_id'], data['name'], data['birth'], data['rank'], data['phone'], et, fee))
        conn.commit()

    return jsonify({'ok': True, 'fee': fee})

@app.route('/api/registrations/<int:tid>', methods=['GET'])
def get_registrations(tid):
    if not session.get('admin'):
        return jsonify({'error': '권한 없음'}), 403
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM registrations WHERE tournament_id=? ORDER BY created_at ASC', (tid,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/registrations/<int:rid>', methods=['DELETE'])
def delete_registration(rid):
    if not session.get('admin'):
        return jsonify({'error': '권한 없음'}), 403
    with get_db() as conn:
        conn.execute('DELETE FROM registrations WHERE id=?', (rid,))
        conn.commit()
    return jsonify({'ok': True})

@app.route('/api/registrations/<int:tid>/export', methods=['GET'])
def export_csv(tid):
    if not session.get('admin'):
        return jsonify({'error': '권한 없음'}), 403
    with get_db() as conn:
        t = conn.execute('SELECT name FROM tournaments WHERE id=?', (tid,)).fetchone()
        rows = conn.execute(
            'SELECT * FROM registrations WHERE tournament_id=? ORDER BY created_at ASC', (tid,)
        ).fetchall()

    lines = ['\ufeff이름,생년월일,단(급),연락처,종목,참가비,신청일시']
    event_map = {'individual': '개인전', 'team': '단체전', 'both': '개인전+단체전'}
    for r in rows:
        lines.append(f"{r['name']},{r['birth']},{r['rank']},{r['phone']},{event_map.get(r['event_type'],r['event_type'])},{r['fee']},{r['created_at']}")

    from flask import Response
    tname = t['name'] if t else '대회'
    return Response(
        '\n'.join(lines),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{tname}_신청현황.csv"'}
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
