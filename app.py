import os
import json
from flask import Flask, redirect, url_for, session, render_template_string
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gibdd-rf-secret-key-2026')

# Автоматическая обработка HTTPS-заголовков Vercel
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Временное хранилище для Vercel (в памяти/tmp)
DATA_DIR = '/tmp' if os.environ.get('VERCEL') else '.'
DATA_FILE = os.path.join(DATA_DIR, 'database.json')

def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# Настройка OAuth (только Google)
oauth = OAuth(app)

oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ФГУП «ГИБДД-РФ» — Единый портал</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #1e1e1e; border: 1px solid #333; border-radius: 12px; width: 100%; max-width: 450px; padding: 30px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        h1 { font-size: 22px; color: #fff; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }
        p.sub { font-size: 13px; color: #888; margin-bottom: 25px; }
        .user-info { background: #2a2a2a; border-radius: 8px; padding: 15px; margin-bottom: 20px; text-align: left; border-left: 4px solid #00a2ff; }
        .user-info p { margin: 4px 0; font-size: 14px; color: #bbb; }
        .btn { display: block; width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; text-decoration: none; color: white; transition: 0.2s; }
        .btn-google { background-color: #ea4335; }
        .btn-roblox-disabled { background-color: #2b2b2b; color: #777; text-decoration: line-through; cursor: not-allowed; pointer-events: none; border: 1px dashed #444; font-size: 13px; }
        .btn-logout { background-color: #333; border: 1px solid #444; color: #aaa; }
        .footer { margin-top: 20px; font-size: 11px; color: #555; }
    </style>
</head>
<body>
    <div class="card">
        <h1>ФГУП «ГИБДД-РФ»</h1>
        <p class="sub">Портал авторизации и доступа к базе данных</p>

        {% if user %}
            <div class="user-info">
                <p><b>Пользователь:</b> {{ user.get('name') }}</p>
                <p><b>Способ входа:</b> {{ user.get('provider') }}</p>
                {% if user.get('email') %}<p><b>Email:</b> {{ user.get('email') }}</p>{% endif %}
                {% if user.get('sub') %}<p><b>ID:</b> {{ user.get('sub') }}</p>{% endif %}
            </div>
            <a href="/logout" class="btn btn-logout">Выйти из системы</a>
        {% else %}
            <p style="margin-bottom: 15px; font-size: 14px;">Авторизуйтесь для доступа:</p>
            <a href="/login/google" class="btn btn-google">Войти через Google</a>
            <div class="btn btn-roblox-disabled">Войти через Roblox (Временно не работает)</div>
        {% endif %}

        <div class="footer">ФГУП «ГИБДД-РФ» &copy; 2026. Системный сервер.</div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, user=session.get('user'))

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('auth_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if user_info:
            user_data = {
                'name': user_info.get('name'),
                'email': user_info.get('email'),
                'provider': 'Google',
                'sub': user_info.get('sub')
            }
            session['user'] = user_data
            db = load_db()
            db[f"google_{user_info.get('sub')}"] = user_data
            save_db(db)
    except Exception as e:
        print(f"Google auth error: {e}")
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

app = app
