import sqlite3
from datetime import datetime
from flask import render_template, request, redirect, url_for
from flaskr import app

DB_NAME = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 打刻履歴テーブル（user_id には社員番号を保存する）
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    # 社員マスタテーブル（社員番号とLINE IDを紐づける）
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            line_user_id TEXT UNIQUE
        )
    ''')

    # テスト用の初期社員データ（すでに登録済みの場合はスキップ）
    sample_employees = [
        ('EMP001', '山田 太郎', '1234', None),
        ('EMP002', '佐藤 花子', '5678', None)
    ]
    c.executemany('''
        INSERT OR IGNORE INTO employees (employee_id, name, password, line_user_id)
        VALUES (?, ?, ?, ?)
    ''', sample_employees)

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    line_user_id = request.args.get('line_user_id', '')
    error_msg = request.args.get('error', '')

    # LINE経由でアクセスした場合（line_user_id が渡されている場合）
    if line_user_id:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT employee_id, name FROM employees WHERE line_user_id = ?', (line_user_id,))
        emp = c.fetchone()

        # 未登録（初回アクセス・機種変更後）の場合は紐づけ画面を表示
        if not emp:
            conn.close()
            return render_template(
                'index.html',
                is_registered=False,
                line_user_id=line_user_id,
                error_msg=error_msg
            )

        # 登録済みの場合は社員情報をセットして履歴を取得
        user_id = emp[0]
        user_name = emp[1]
        c.execute(
            'SELECT user_name, action, timestamp FROM records WHERE user_id = ? ORDER BY id DESC LIMIT 20',
            (user_id,)
        )
        records = c.fetchall()
        conn.close()

        last_action = records[0][1] if records else None
        return render_template(
            'index.html',
            is_registered=True,
            records=records,
            last_action=last_action,
            user_id=user_id,
            user_name=user_name,
            line_user_id=line_user_id
        )

    # PCブラウザ等で直接開いた場合のテスト用フォールバック
    user_id = request.args.get('user_id', 'EMP001')
    user_name = request.args.get('user_name', '山田 太郎')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        'SELECT user_name, action, timestamp FROM records WHERE user_id = ? ORDER BY id DESC LIMIT 20',
        (user_id,)
    )
    records = c.fetchall()
    conn.close()
    last_action = records[0][1] if records else None

    return render_template(
        'index.html',
        is_registered=True,
        records=records,
        last_action=last_action,
        user_id=user_id,
        user_name=user_name,
        line_user_id=''
    )

@app.route('/register', methods=['POST'])
def register():
    line_user_id = request.form.get('line_user_id', '').strip()
    employee_id = request.form.get('employee_id', '').strip().upper()
    password = request.form.get('password', '').strip()

    if not line_user_id or not employee_id or not password:
        return redirect(url_for('index', line_user_id=line_user_id, error='すべての項目を入力してください'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT name, password, line_user_id FROM employees WHERE employee_id = ?', (employee_id,))
    emp = c.fetchone()

    if not emp:
        conn.close()
        return redirect(url_for('index', line_user_id=line_user_id, error='社員番号が見つかりません'))

    db_name = emp[0]
    db_password = emp[1]
    db_line_id = emp[2]

    if db_password != password:
        conn.close()
        return redirect(url_for('index', line_user_id=line_user_id, error='パスワードが間違っています'))

    if db_line_id is not None and db_line_id != line_user_id:
        conn.close()
        return redirect(url_for('index', line_user_id=line_user_id, error='この社員番号はすでに別のLINEと連携済みです'))

    # 認証成功：LINE IDを社員マスタに紐づける
    c.execute('UPDATE employees SET line_user_id = ? WHERE employee_id = ?', (line_user_id, employee_id))
    conn.commit()
    conn.close()

    return redirect(url_for('index', line_user_id=line_user_id))

@app.route('/stamp', methods=['POST'])
def stamp():
    user_id = request.form.get('user_id')
    user_name = request.form.get('user_name')
    line_user_id = request.form.get('line_user_id', '')
    action = request.form.get('action')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    valid_actions = ['出勤', '休憩開始', '休憩終了', '退勤']
    if action in valid_actions and user_id:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute('SELECT action FROM records WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
        row = c.fetchone()
        last_action = row[0] if row else None

        is_allowed = False
        if action == '出勤' and last_action in [None, '退勤']:
            is_allowed = True
        elif action in ['休憩開始', '退勤'] and last_action in ['出勤', '休憩終了']:
            is_allowed = True
        elif action == '休憩終了' and last_action == '休憩開始':
            is_allowed = True

        if is_allowed:
            c.execute(
                'INSERT INTO records (user_id, user_name, action, timestamp) VALUES (?, ?, ?, ?)',
                (user_id, user_name, action, now)
            )
            conn.commit()
            
        conn.close()

    if line_user_id:
        return redirect(url_for('index', line_user_id=line_user_id))
    return redirect(url_for('index', user_id=user_id, user_name=user_name))
