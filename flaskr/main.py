import sqlite3
from datetime import datetime
from flask import render_template, request, redirect, url_for
from flaskr import app

DB_NAME = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    user_id = request.args.get('user_id', 'test_user_1')
    user_name = request.args.get('user_name', 'テスト太郎')

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute(
        'SELECT user_name, action, timestamp FROM records WHERE user_id = ? ORDER BY id DESC LIMIT 20',
        (user_id,)
    )
    records = c.fetchall()
    conn.close()
    
    # 最新1件目(records[0])の、2番目の項目([1]＝打刻種別)を取得
    last_action = records[0][1] if records else None
    
    return render_template(
        'index.html',
        records=records,
        last_action=last_action,
        user_id=user_id,
        user_name=user_name
    )

@app.route('/stamp', methods=['POST'])
def stamp():
    user_id = request.form.get('user_id', 'test_user_1')
    user_name = request.form.get('user_name', 'テスト太郎')
    action = request.form.get('action')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    valid_actions = ['出勤', '休憩開始', '休憩終了', '退勤']
    if action in valid_actions:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute('SELECT action FROM records WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
        row = c.fetchone()
        # 取得した1行(row)の最初の項目([0])を取得
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

    return redirect(url_for('index', user_id=user_id, user_name=user_name))
