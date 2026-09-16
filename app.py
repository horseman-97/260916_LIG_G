import os
import sys
import psycopg2
import psycopg2.extras
from datetime import datetime, date, timedelta
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
app.config['SECRET_KEY'] = 'lig-dna-todo-secret-key-2026'

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

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT '업무/프로젝트',
            priority TEXT DEFAULT '보통',
            due_date TEXT DEFAULT '',
            completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    ''')
    conn.commit()

    # Check if empty, insert default initial sample data
    cursor.execute('SELECT COUNT(*) as count FROM todos')
    if cursor.fetchone()['count'] == 0:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        in_3_days = today + timedelta(days=3)
        in_5_days = today + timedelta(days=5)
        in_7_days = today + timedelta(days=7)

        sample_tasks = [
            (
                'LIG DNA 3분기 디지털 혁신 역량 강화 과제 발표 준비',
                'RPA 및 AI 도구를 접목한 실무 업무 혁신 사례 요약 슬라이드 작성 및 데모 시연 준비',
                'DNA 과제',
                '높음',
                tomorrow.strftime('%Y-%m-%d'),
                0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                None
            ),
            (
                'Python Flask 기반 스마트 투두 시스템 환경 점검 및 배포',
                '로컬 개발 환경 구축 및 웹 서비스 기본 라우팅 검증 완료',
                '업무/프로젝트',
                '보통',
                today.strftime('%Y-%m-%d'),
                1,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ),
            (
                '주간 RPA 자동화 워크플로우 운영 현황 보고서 작성',
                '업무 자동화 성과 지표(시간 절감량, 처리 건수) 취합 및 보고 자료 구성',
                '업무/프로젝트',
                '높음',
                in_3_days.strftime('%Y-%m-%d'),
                0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                None
            ),
            (
                '생성형 AI 프롬프트 엔지니어링 실무 기법 스터디',
                '업무 생산성 극대화를 위한 맞춤형 템플릿 및 자동화 연계 방안 학습',
                '개인/자기계발',
                '보통',
                in_5_days.strftime('%Y-%m-%d'),
                0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                None
            ),
            (
                '스마트 워크플레이스 개선 아이디어 브레인스토밍 회의',
                '팀 내 업무 효율 향상을 위한 신규 협업 툴 도입 및 프로세스 개선 토론',
                '회의/미팅',
                '낮음',
                in_7_days.strftime('%Y-%m-%d'),
                0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                None
            )
        ]

        cursor.executemany('''
            INSERT INTO todos (title, description, category, priority, due_date, completed, created_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', sample_tasks)
        conn.commit()

    conn.close()

# Initialize DB when app starts
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/todos', methods=['GET'])
def get_todos():
    status = request.args.get('status', 'all')
    category = request.args.get('category', 'all')
    priority = request.args.get('priority', 'all')
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'created_desc')

    conn = get_db()
    cursor = conn.cursor()

    query = 'SELECT * FROM todos WHERE 1=1'
    params = []

    if status == 'active':
        query += ' AND completed = 0'
    elif status == 'completed':
        query += ' AND completed = 1'

    if category and category != 'all':
        query += ' AND category = %s'
        params.append(category)

    if priority and priority != 'all':
        query += ' AND priority = %s'
        params.append(priority)

    if search:
        query += ' AND (title LIKE %s OR description LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%'])

    # Sorting
    if sort_by == 'due_date':
        query += " ORDER BY CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END, due_date ASC, id DESC"
    elif sort_by == 'priority':
        query += """
            ORDER BY CASE priority
                WHEN '높음' THEN 1
                WHEN '보통' THEN 2
                WHEN '낮음' THEN 3
                ELSE 4
            END, id DESC
        """
    elif sort_by == 'created_asc':
        query += ' ORDER BY id ASC'
    else:  # created_desc
        query += ' ORDER BY id DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    todos = [dict(row) for row in rows]
    conn.close()

    return jsonify(todos)

@app.route('/api/todos', methods=['POST'])
def add_todo():
    data = request.get_json() or {}
    title = data.get('title', '').strip()

    if not title:
        return jsonify({'error': '할 일 제목을 입력해주세요.'}), 400

    description = data.get('description', '').strip()
    category = data.get('category', '업무/프로젝트')
    priority = data.get('priority', '보통')
    due_date = data.get('due_date', '').strip()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO todos (title, description, category, priority, due_date, completed, created_at)
        VALUES (%s, %s, %s, %s, %s, 0, %s)
        RETURNING id
    ''', (title, description, category, priority, due_date, now_str))
    new_id = cursor.fetchone()['id']
    conn.commit()

    cursor.execute('SELECT * FROM todos WHERE id = %s', (new_id,))
    todo = dict(cursor.fetchone())
    conn.close()

    return jsonify(todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['GET'])
def get_todo(todo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE id = %s', (todo_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': '해당 할 일을 찾을 수 없습니다.'}), 404

    return jsonify(dict(row))

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.get_json() or {}
    title = data.get('title', '').strip()

    if not title:
        return jsonify({'error': '할 일 제목을 입력해주세요.'}), 400

    description = data.get('description', '').strip()
    category = data.get('category', '업무/프로젝트')
    priority = data.get('priority', '보통')
    due_date = data.get('due_date', '').strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE todos
        SET title = %s, description = %s, category = %s, priority = %s, due_date = %s
        WHERE id = %s
    ''', (title, description, category, priority, due_date, todo_id))
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': '해당 할 일을 찾을 수 없습니다.'}), 404

    cursor.execute('SELECT * FROM todos WHERE id = %s', (todo_id,))
    todo = dict(cursor.fetchone())
    conn.close()

    return jsonify(todo)

@app.route('/api/todos/<int:todo_id>/toggle', methods=['PATCH'])
def toggle_todo(todo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT completed FROM todos WHERE id = %s', (todo_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'error': '해당 할 일을 찾을 수 없습니다.'}), 404

    new_status = 0 if row['completed'] == 1 else 1
    completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if new_status == 1 else None

    cursor.execute('''
        UPDATE todos
        SET completed = %s, completed_at = %s
        WHERE id = %s
    ''', (new_status, completed_at, todo_id))
    conn.commit()

    cursor.execute('SELECT * FROM todos WHERE id = %s', (todo_id,))
    todo = dict(cursor.fetchone())
    conn.close()

    return jsonify(todo)

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM todos WHERE id = %s', (todo_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()

    if not deleted:
        return jsonify({'error': '해당 할 일을 찾을 수 없습니다.'}), 404

    return jsonify({'success': True, 'message': '삭제되었습니다.'})

@app.route('/api/todos/clear-completed', methods=['POST'])
def clear_completed():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM todos WHERE completed = 1')
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'deleted_count': deleted_count})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as total FROM todos')
    total = cursor.fetchone()['total']

    cursor.execute('SELECT COUNT(*) as completed FROM todos WHERE completed = 1')
    completed = cursor.fetchone()['completed']

    active = total - completed
    rate = round((completed / total * 100), 1) if total > 0 else 0

    # Category stats
    cursor.execute('SELECT category, COUNT(*) as count FROM todos GROUP BY category')
    category_counts = {row['category']: row['count'] for row in cursor.fetchall()}

    # Priority stats (active only)
    cursor.execute('SELECT priority, COUNT(*) as count FROM todos WHERE completed = 0 GROUP BY priority')
    priority_counts = {row['priority']: row['count'] for row in cursor.fetchall()}

    # Due today count
    today_str = date.today().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) as count FROM todos WHERE completed = 0 AND due_date = %s', (today_str,))
    due_today = cursor.fetchone()['count']

    conn.close()

    return jsonify({
        'total': total,
        'completed': completed,
        'active': active,
        'rate': rate,
        'due_today': due_today,
        'category_counts': category_counts,
        'priority_counts': priority_counts
    })

if __name__ == '__main__':
    # Host 127.0.0.1, port 5000 with debug disabled for stability
    print("==================================================")
    print("  [LIG DNA SMART TODO APP] Server Started")
    print("  URL: http://127.0.0.1:5000")
    print("==================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
