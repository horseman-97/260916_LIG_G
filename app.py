import os
import sys
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlencode, parse_qsl
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lig-dna-worktime-secret-key-2026'

# libpq/psycopg2 only understands a specific set of DSN query params. Some
# providers (e.g. Supabase) append extra tracking params to the connection
# string that make psycopg2 reject the DSN, so strip anything unrecognized.
_LIBPQ_PARAMS = {
    'sslmode', 'sslrootcert', 'sslcert', 'sslkey', 'connect_timeout',
    'application_name', 'options', 'target_session_attrs', 'gssencmode',
}

def _sanitize_dsn(url):
    parsed = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parsed.query) if k in _LIBPQ_PARAMS]
    return parsed._replace(query=urlencode(query)).geturl()

DATABASE_URL = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError(
        'POSTGRES_URL (or DATABASE_URL) environment variable is required. '
        'Set it in a local .env file or in the Vercel project settings.'
    )
DATABASE_URL = _sanitize_dsn(DATABASE_URL)

# The app has no login system (single personal user), but the schema keeps a
# user_id column so multi-user support can be added later without migrating.
USER_ID = 'default'
DEFAULT_BREAK_MINUTES = 60
DEFAULT_TARGET_MINUTES = 480  # 8 hours
DT_FMT = '%Y-%m-%d %H:%M:%S'
KST = timezone(timedelta(hours=9))

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_records (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            work_date TEXT NOT NULL,
            clock_in TEXT,
            clock_out TEXT,
            break_minutes INTEGER NOT NULL DEFAULT 60,
            work_minutes INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (user_id, work_date)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB when app starts
init_db()

def now_kst():
    return datetime.now(KST)

def today_str():
    return now_kst().strftime('%Y-%m-%d')

def is_valid_date(value):
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False

def is_valid_datetime(value):
    try:
        datetime.strptime(value, DT_FMT)
        return True
    except (ValueError, TypeError):
        return False

def compute_work_minutes(clock_in_str, clock_out_str, break_minutes):
    t_in = datetime.strptime(clock_in_str, DT_FMT)
    t_out = datetime.strptime(clock_out_str, DT_FMT)
    total_minutes = int((t_out - t_in).total_seconds() // 60)
    return max(total_minutes - break_minutes, 0)

def serialize_record(row):
    data = dict(row)
    if data.get('clock_out'):
        data['status'] = 'done'
    elif data.get('clock_in'):
        data['status'] = 'working'
    else:
        data['status'] = 'not_started'
    return data

def empty_record(work_date):
    return {
        'work_date': work_date,
        'clock_in': None,
        'clock_out': None,
        'break_minutes': DEFAULT_BREAK_MINUTES,
        'work_minutes': None,
        'status': 'not_started',
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/work/today', methods=['GET'])
def work_today():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM work_records WHERE user_id = %s AND work_date = %s',
        (USER_ID, today_str())
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        data = empty_record(today_str())
    else:
        data = serialize_record(row)

    data['target_minutes'] = DEFAULT_TARGET_MINUTES
    data['expected_clock_out'] = None
    if data['clock_in'] and not data['clock_out']:
        t_in = datetime.strptime(data['clock_in'], DT_FMT)
        break_minutes = data['break_minutes'] or 0
        expected = t_in + timedelta(minutes=DEFAULT_TARGET_MINUTES + break_minutes)
        data['expected_clock_out'] = expected.strftime(DT_FMT)

    return jsonify(data)

@app.route('/api/work/clock-in', methods=['POST'])
def clock_in():
    conn = get_db()
    cursor = conn.cursor()
    today = today_str()
    cursor.execute(
        'SELECT * FROM work_records WHERE user_id = %s AND work_date = %s',
        (USER_ID, today)
    )
    row = cursor.fetchone()

    if row and row['clock_in']:
        conn.close()
        return jsonify({'error': '이미 오늘 출근 기록이 있습니다.'}), 400

    now_str = now_kst().strftime(DT_FMT)
    try:
        if row:
            cursor.execute(
                'UPDATE work_records SET clock_in = %s, updated_at = %s WHERE id = %s',
                (now_str, now_str, row['id'])
            )
            record_id = row['id']
        else:
            cursor.execute('''
                INSERT INTO work_records (user_id, work_date, clock_in, break_minutes, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (USER_ID, today, now_str, DEFAULT_BREAK_MINUTES, now_str, now_str))
            record_id = cursor.fetchone()['id']
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return jsonify({'error': '출근 기록을 저장하지 못했습니다. 잠시 후 다시 시도해주세요.'}), 500

    cursor.execute('SELECT * FROM work_records WHERE id = %s', (record_id,))
    result = serialize_record(cursor.fetchone())
    conn.close()
    return jsonify(result), 201

@app.route('/api/work/clock-out', methods=['POST'])
def clock_out():
    conn = get_db()
    cursor = conn.cursor()
    today = today_str()
    cursor.execute(
        'SELECT * FROM work_records WHERE user_id = %s AND work_date = %s',
        (USER_ID, today)
    )
    row = cursor.fetchone()

    if not row or not row['clock_in']:
        conn.close()
        return jsonify({'error': '출근 기록이 없어 퇴근할 수 없습니다.'}), 400

    if row['clock_out']:
        conn.close()
        return jsonify({'error': '이미 퇴근 처리된 근무 기록입니다.'}), 400

    now_str = now_kst().strftime(DT_FMT)
    break_minutes = row['break_minutes'] if row['break_minutes'] is not None else DEFAULT_BREAK_MINUTES
    work_minutes = compute_work_minutes(row['clock_in'], now_str, break_minutes)

    try:
        cursor.execute('''
            UPDATE work_records
            SET clock_out = %s, work_minutes = %s, updated_at = %s
            WHERE id = %s
        ''', (now_str, work_minutes, now_str, row['id']))
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return jsonify({'error': '퇴근 기록을 저장하지 못했습니다. 잠시 후 다시 시도해주세요.'}), 500

    cursor.execute('SELECT * FROM work_records WHERE id = %s', (row['id'],))
    result = serialize_record(cursor.fetchone())
    conn.close()
    return jsonify(result)

@app.route('/api/work/records', methods=['GET'])
def list_records():
    limit = request.args.get('limit', 30, type=int)
    limit = max(1, min(limit, 365))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM work_records
        WHERE user_id = %s
        ORDER BY work_date DESC
        LIMIT %s
    ''', (USER_ID, limit))
    rows = [serialize_record(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify(rows)

@app.route('/api/work/records/<work_date>', methods=['GET'])
def get_record_by_date(work_date):
    if not is_valid_date(work_date):
        return jsonify({'error': '날짜 형식이 올바르지 않습니다.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM work_records WHERE user_id = %s AND work_date = %s',
        (USER_ID, work_date)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify(empty_record(work_date))

    return jsonify(serialize_record(row))

@app.route('/api/work/records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM work_records WHERE id = %s AND user_id = %s',
        (record_id, USER_ID)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': '해당 근무 기록을 찾을 수 없습니다.'}), 404

    clock_in_val = data.get('clock_in', row['clock_in']) or None
    clock_out_val = data.get('clock_out', row['clock_out']) or None
    break_minutes = data.get('break_minutes', row['break_minutes'])

    try:
        break_minutes = int(break_minutes)
    except (TypeError, ValueError):
        conn.close()
        return jsonify({'error': '휴게시간 형식이 올바르지 않습니다.'}), 400
    if break_minutes < 0:
        conn.close()
        return jsonify({'error': '휴게시간은 0 이상이어야 합니다.'}), 400

    for value, label in ((clock_in_val, '출근'), (clock_out_val, '퇴근')):
        if value and not is_valid_datetime(value):
            conn.close()
            return jsonify({'error': f'{label} 시간 형식이 올바르지 않습니다.'}), 400

    if clock_out_val and not clock_in_val:
        conn.close()
        return jsonify({'error': '출근 시간 없이 퇴근 시간만 저장할 수 없습니다.'}), 400

    work_minutes = None
    if clock_in_val and clock_out_val:
        if clock_out_val <= clock_in_val:
            conn.close()
            return jsonify({'error': '퇴근 시간은 출근 시간보다 늦어야 합니다.'}), 400
        work_minutes = compute_work_minutes(clock_in_val, clock_out_val, break_minutes)

    now_str = now_kst().strftime(DT_FMT)
    try:
        cursor.execute('''
            UPDATE work_records
            SET clock_in = %s, clock_out = %s, break_minutes = %s, work_minutes = %s, updated_at = %s
            WHERE id = %s
        ''', (clock_in_val, clock_out_val, break_minutes, work_minutes, now_str, record_id))
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return jsonify({'error': '근무 기록을 수정하지 못했습니다. 잠시 후 다시 시도해주세요.'}), 500

    cursor.execute('SELECT * FROM work_records WHERE id = %s', (record_id,))
    result = serialize_record(cursor.fetchone())
    conn.close()
    return jsonify(result)

@app.route('/api/work/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM work_records WHERE id = %s AND user_id = %s',
        (record_id, USER_ID)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()

    if not deleted:
        return jsonify({'error': '해당 근무 기록을 찾을 수 없습니다.'}), 404

    return jsonify({'success': True, 'message': '삭제되었습니다.'})

@app.route('/api/work/summary/weekly', methods=['GET'])
def weekly_summary():
    ref_str = request.args.get('date', today_str())
    if not is_valid_date(ref_str):
        return jsonify({'error': '날짜 형식이 올바르지 않습니다.'}), 400

    ref = datetime.strptime(ref_str, '%Y-%m-%d').date()
    monday = ref - timedelta(days=ref.weekday())
    sunday = monday + timedelta(days=6)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT work_date, work_minutes FROM work_records
        WHERE user_id = %s AND work_date >= %s AND work_date <= %s
    ''', (USER_ID, monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')))
    minutes_by_date = {r['work_date']: (r['work_minutes'] or 0) for r in cursor.fetchall()}
    conn.close()

    days = []
    total_minutes = 0
    for i in range(7):
        d = monday + timedelta(days=i)
        d_str = d.strftime('%Y-%m-%d')
        minutes = minutes_by_date.get(d_str, 0)
        total_minutes += minutes
        days.append({'date': d_str, 'work_minutes': minutes})

    return jsonify({
        'week_start': monday.strftime('%Y-%m-%d'),
        'week_end': sunday.strftime('%Y-%m-%d'),
        'days': days,
        'total_minutes': total_minutes,
    })

@app.route('/api/work/summary/monthly', methods=['GET'])
def monthly_summary():
    year = request.args.get('year', type=int) or now_kst().year
    month = request.args.get('month', type=int) or now_kst().month
    if month < 1 or month > 12:
        return jsonify({'error': '월 형식이 올바르지 않습니다.'}), 400

    prefix = f'{year:04d}-{month:02d}'
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT work_minutes FROM work_records
        WHERE user_id = %s AND work_date LIKE %s AND work_minutes IS NOT NULL
    ''', (USER_ID, f'{prefix}-%'))
    minutes_list = [r['work_minutes'] for r in cursor.fetchall()]
    conn.close()

    work_days = len(minutes_list)
    total_minutes = sum(minutes_list)
    avg_minutes = round(total_minutes / work_days) if work_days else 0

    return jsonify({
        'year': year,
        'month': month,
        'work_days': work_days,
        'total_minutes': total_minutes,
        'avg_minutes': avg_minutes,
    })

if __name__ == '__main__':
    # Host 127.0.0.1, port 5000 with debug disabled for stability
    print("==================================================")
    print("  [LIG DNA WORK TIME APP] Server Started")
    print("  URL: http://127.0.0.1:5000")
    print("==================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
