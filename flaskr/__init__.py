
from flask import Flask

app = Flask(__name__)

# セッション管理用の秘密鍵
app.secret_key = 'dev-secret-key-change-this'

import flaskr.main
