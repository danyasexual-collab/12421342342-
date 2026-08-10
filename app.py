import os
import json
from flask import Flask, redirect, url_for, session, render_template_string
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gibdd-rf-secret-key-2026')

# Автоматическая обработка HTTPS-заголовков Vercel
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Временное хранилище для Vercel
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

# Настройка OAuth (Google + Discord)
oauth = OAuth(app)

oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)

oauth.register(
    name='discord',
    client_id=os.environ.get('DISCORD_CLIENT_ID'),
    client_secret=os.environ.get('DISCORD_CLIENT_SECRET'),
    access_token_url='https://discord.com/api/oauth2/token',
    authorize_url='https://discord.com/api/oauth2/authorize',
    api_base_url='https://discord.com/api/',
    client_kwargs={'scope': 'identify email'}
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ФГУП «ГИБДД-РФ» — Портал государственной регистрации</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b0e14; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #131822; border: 1px solid #1f293d; border-radius: 12px; width: 100%; max-width: 750px; padding: 30px; box-shadow: 0 12px 32px rgba(0,0,0,0.6); }
        .header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #1f293d; padding-bottom: 15px; }
        h1 { font-size: 20px; color: #fff; text-transform: uppercase; letter-spacing: 1px; }
        p.sub { font-size: 12px; color: #8a99ad; }
        
        .dashboard { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px; }
        .panel { background: #182030; border: 1px solid #243049; border-radius: 8px; padding: 18px; transition: 0.2s; cursor: pointer; }
        .panel:hover { border-color: #00a2ff; transform: translateY(-2px); }
        .panel h3 { font-size: 15px; color: #38bdf8; margin-bottom: 6px; }
        .panel p { font-size: 12px; color: #94a3b8; line-height: 1.4; }
        
        .user-badge { background: #182030; border-left: 4px solid #38bdf8; padding: 14px; border-radius: 6px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .user-info p { margin: 3px 0; font-size: 13px; color: #cbd5e1; }
        .user-info b { color: #fff; }
        
        .btn { display: block; width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; text-decoration: none; color: white; text-align: center; transition: 0.2s; }
        .btn-google { background-color: #ea4335; }
        .btn-google:hover { background-color: #d33426; }
        .btn-discord { background-color: #5865F2; }
        .btn-discord:hover { background-color: #4752c4; }
        .btn-disabled { background-color: #1a2233; color: #55627a; text-decoration: line-through; cursor: not-allowed; pointer-events: none; border: 1px dashed #2a3852; font-size: 13px; }
        .btn-logout { background-color: #26171a; border: 1px solid #4a2228; color: #f87171; width: auto; padding: 8px 16px; margin: 0; font-size: 12px; }
        .btn-logout:hover { background-color: #3b1b22; }
        
        .footer { margin-top: 20px; font-size: 11px; color: #475569; text-align: center; }
        .center-box { text-align: center; max-width: 420px; margin: 0 auto; }
    </style>
</head>
<body>
    <div class="card">
        {% if user %}
            <div class="header-flex">
                <div>
                    <h1>ФГУП «ГИБДД-РФ»</h1>
                    <p class="sub">Государственный реестр и учет транспортных средств</p>
                </div>
                <a href="/logout" class="btn btn-logout">Выйти</a>
            </div>

            <div class="user-badge">
                <div class="user-info">
                    <p><b>Гражданин / Сотрудник:</b> {{ user.get('name') }}</p>
                    <p><b>Идентификатор входа:</b> {{ user.get('provider') }}</p>
                    {% if user.get('email') %}<p><b>Email:</b> {{ user.get('email') }}</p>{% endif %}
                </div>
            </div>

            <div class="dashboard">
                <div class="panel">
                    <h3>🚗 Регистрация ТС</h3>
                    <p>Постановка на учет личного и служебного автотранспорта, выдача свидетельств.</p>
                </div>
                <div class="panel">
                    <h3>💎 Биржа блатных номеров</h3>
                    <p>Покупка, продажа и аукцион эксклюзивных государственных регистрационных знаков.</p>
                </div>
                <div class="panel">
                    <h3>📋 Учет игроков</h3>
                    <p>Регистрация профилей сотрудников и граждан в единой базе данных ГИБДД.</p>
                </div>
                <div class="panel">
                    <h3>⚠️ База штрафов и розыска</h3>
                    <p>Проверка транспортных средств на наличие ограничений, штрафов и ориентировок.</p>
                </div>
            </div>
        {% else %}
            <div class="center-box">
                <h1>ФГУП «ГИБДД-РФ»</h1>
                <p class="sub" style="margin-bottom: 25px;">Единый портал авторизации игроков</p>
                <p style="margin-bottom: 15px; font-size: 14px; color: #94a3b8;">Выберите способ входа в систему:</p>
                <a href="/login/google" class="btn btn-google">Войти через Google</a>
                <a href="/login/discord" class="btn btn-discord">Войти через Discord (Beta)</a>
                <div class="btn btn-disabled">Войти через Roblox (Временно не работает)</div>
            </div>
        {% endif %}

        <div class="footer">ФГУП «ГИБДД-РФ» &copy; 2026. Официальный серверный реестр.</div>
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

@app.route('/login/discord')
def login_discord():
    redirect_uri = 'https://gibdd-russia-rp.vercel.app/auth/discord/callback'
    return oauth.discord.authorize_redirect(redirect_uri)

@app.route('/auth/discord/callback')
def auth_discord():
    try:
        token = oauth.discord.authorize_access_token()
        resp = oauth.discord.get('users/@me', token=token)
        user_info = resp.json()
        if user_info:
            user_data = {
                'name': f"{user_info.get('username')}#{user_info.get('discriminator', '0')}" if user_info.get('discriminator') and user_info.get('discriminator') != '0' else user_info.get('username'),
                'email': user_info.get('email'),
                'provider': 'Discord',
                'sub': user_info.get('id')
            }
            session['user'] = user_data
            db = load_db()
            db[f"discord_{user_info.get('id')}"] = user_data
            save_db(db)
    except Exception as e:
        print(f"Discord auth error: {e}")
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

app = app
