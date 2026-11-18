import sqlite3
from datetime import datetime
from flask import render_template, request, redirect, url_for, session
from flaskr import app

DB_NAME = "attendance.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 打刻履歴テーブル（user_id には社員番号を保存する）
    # 勤怠テーブル作成　あとから別ファイルにまとめる　触るな！！
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
    # 社員情報作成テーブル　あとから別ファイルにまとめる　触るな！！
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            line_user_id TEXT UNIQUE
        )
    ''')

    # テスト用の初期社員データ（すでに登録済みの場合はスキップ）
    # Noneはnullって意味間違えないこと！！SQLではNULLとして扱われる
    sample_employees = [
        ('EMP001', '山田 太郎', '1234', None),
        ('EMP002', '佐藤 花子', '5678', None)
    ]

    # 複数のデータをまとめてSQLに登録する
    c.executemany('''
        INSERT OR IGNORE INTO employees (employee_id, name, password, line_user_id)
        VALUES (?, ?, ?, ?)
    ''', sample_employees)

    conn.commit()
    conn.close()


# ここで関数実行されている
init_db()


# 管理者ログイン画面・認証処理
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():

    # ログインボタンが押された場合
    if request.method == 'POST':

        # HTMLから管理者IDとパスワードを取得
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # adminsテーブルから管理者情報を検索
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            'SELECT admin_id FROM admins WHERE username = ? AND password = ? AND is_active = 1',
            (username, password)
        )
        admin = c.fetchone()
        conn.close()

        # 管理者が見つかった場合
        if admin:
            session['admin_id'] = admin[0]
            return redirect(url_for('admin_dashboard'))

        # IDまたはパスワードが間違っている場合
        return render_template(
            'admin_login.html',
            error_msg='管理者IDまたはパスワードが間違っています'
        )

    return render_template('admin_login.html')


# 管理者トップ画面
@app.route('/admin')
def admin_dashboard():

    # ログインしていない場合はログイン画面に戻す
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    return render_template('admin.html')


# トップページにアクセスされるとindexが実行される
@app.route('/')
def index():

    # URLからLINEユーザーIDとエラーメッセージを取得する
    line_user_id = request.args.get('line_user_id', '')
    error_msg = request.args.get('error', '')
    mode = request.args.get('mode', '')

    # LINE経由でアクセスして、まだスタッフを選択していない場合
    # 最初の選択画面を表示する
    if line_user_id and mode != 'staff':
        return render_template(
            'index.html',
            mode='select',
            line_user_id=line_user_id
        )

    # LINE経由でスタッフとして利用する場合
    if line_user_id:

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute(
            'SELECT employee_id, name FROM employees WHERE line_user_id = ?',
            (line_user_id,)
        )
        emp = c.fetchone()

        # 未登録（初回アクセス・機種変更後）の場合は紐づけ画面を表示
        if not emp:
            conn.close()
            return render_template(
                'index.html',
                mode='staff',
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

        # 最後に行った打刻を取得する
        last_action = records[0][1] if records else None

        # HTMLにデータを渡す
        return render_template(
            'index.html',
            mode='staff',
            is_registered=True,
            records=records,
            last_action=last_action,
            user_id=user_id,
            user_name=user_name,
            line_user_id=line_user_id
        )

    # PCブラウザ等で直接開いた場合のテスト用
    # URLから社員番号を取得して表示している
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

    # HTMLの画面表示
    return render_template(
        'index.html',
        mode='staff',
        is_registered=True,
        records=records,
        last_action=last_action,
        user_id=user_id,
        user_name=user_name,
        line_user_id=''
    )


# 社員番号とパスワードで本人確認をして、LINEアカウントと社員情報を連携させる処理
@app.route('/register', methods=['POST'])
def register():

    # HTMLのフォームから送信された情報を取得
    line_user_id = request.form.get('line_user_id', '').strip()
    employee_id = request.form.get('employee_id', '').strip().upper()
    password = request.form.get('password', '').strip()

    # 入力漏れがないか確認
    if not line_user_id or not employee_id or not password:
        return redirect(url_for(
            'index',
            line_user_id=line_user_id,
            mode='staff',
            error='すべての項目を入力してください'
        ))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 社員番号を使って社員情報を検索
    c.execute(
        'SELECT name, password, line_user_id FROM employees WHERE employee_id = ?',
        (employee_id,)
    )
    emp = c.fetchone()

    # 社員番号が存在するか確認
    if not emp:
        conn.close()
        return redirect(url_for(
            'index',
            line_user_id=line_user_id,
            mode='staff',
            error='社員番号が見つかりません'
        ))

    # データベースから取得した情報を変数に格納
    db_name = emp[0]
    db_password = emp[1]
    db_line_id = emp[2]

    # 入力されたパスワードとDBのパスワードを比較
    if db_password != password:
        conn.close()
        return redirect(url_for(
            'index',
            line_user_id=line_user_id,
            mode='staff',
            error='パスワードが間違っています'
        ))

    # 別のLINEと連携されていないか確認する
    if db_line_id is not None and db_line_id != line_user_id:
        conn.close()
        return redirect(url_for(
            'index',
            line_user_id=line_user_id,
            mode='staff',
            error='この社員番号はすでに別のLINEと連携済みです'
        ))

    # LINE IDを社員情報に登録する
    c.execute(
        'UPDATE employees SET line_user_id = ? WHERE employee_id = ?',
        (line_user_id, employee_id)
    )

    conn.commit()
    conn.close()

    # 登録完了後、スタッフ画面に戻る
    return redirect(url_for(
        'index',
        line_user_id=line_user_id,
        mode='staff'
    ))


@app.route('/stamp', methods=['POST'])
def stamp():

    # HTMLから渡されたフォーム情報を取得している
    user_id = request.form.get('user_id')
    user_name = request.form.get('user_name')
    line_user_id = request.form.get('line_user_id', '')
    action = request.form.get('action')

    # 現在の日時を取得して、指定した形式の文字列に変換
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 打刻できる操作を設定している
    valid_actions = ['出勤', '休憩開始', '休憩終了', '退勤']

    # 打刻内容と社員番号を確認
    if action in valid_actions and user_id:

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 社員の最新の打刻内容を取得する
        c.execute(
            'SELECT action FROM records WHERE user_id = ? ORDER BY id DESC LIMIT 1',
            (user_id,)
        )
        row = c.fetchone()
        last_action = row[0] if row else None

        # 打刻を許可するか、条件を満たした場合Trueに変更
        is_allowed = False

        if action == '出勤' and last_action in [None, '退勤']:
            is_allowed = True

        elif action in ['休憩開始', '退勤'] and last_action in ['出勤', '休憩終了']:
            is_allowed = True

        elif action == '休憩終了' and last_action == '休憩開始':
            is_allowed = True

        # 打刻が許可されている場合だけDBに保存する
        if is_allowed:
            c.execute(
                'INSERT INTO records (user_id, user_name, action, timestamp) VALUES (?, ?, ?, ?)',
                (user_id, user_name, action, now)
            )
            conn.commit()

        conn.close()

    # 打刻後画面に戻る
    # テスト版とLINE各々変更している
    if line_user_id:
        return redirect(url_for(
            'index',
            line_user_id=line_user_id,
            mode='staff'
        ))

    return redirect(url_for(
        'index',
        user_id=user_id,
        user_name=user_name
    ))