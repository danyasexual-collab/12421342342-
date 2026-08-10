import os
import json
from flask import Flask, redirect, url_for, session, render_template_string, request
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gibdd-rf-secret-key-2026')

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

DATA_DIR = '/tmp' if os.environ.get('VERCEL') else '.'
DATA_FILE = os.path.join(DATA_DIR, 'database.json')

OWNER_EMAIL = 'danyasexual@gmail.com'

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
    <title>ФГУП «ГИБДД-РФ» — Портал управления</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b0e14; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #131822; border: 1px solid #1f293d; border-radius: 12px; width: 100%; max-width: 850px; padding: 25px; box-shadow: 0 12px 32px rgba(0,0,0,0.6); }
        
        .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #1f293d; padding-bottom: 15px; }
        .brand { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: bold; color: #fff; text-transform: uppercase; }
        .online-status { font-size: 12px; color: #22c55e; display: flex; align-items: center; gap: 6px; }
        .online-dot { width: 8px; height: 8px; background-color: #22c55e; border-radius: 50%; box-shadow: 0 0 8px #22c55e; }

        .nav-tabs { display: flex; gap: 8px; margin-bottom: 20px; background: #182030; padding: 8px; border-radius: 8px; border: 1px solid #243049; }
        .nav-btn { background: #131822; border: 1px solid #243049; color: #94a3b8; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: 0.2s; display: flex; align-items: center; gap: 6px; }
        .nav-btn:hover, .nav-btn.active { background: #00a2ff; color: #fff; border-color: #00a2ff; }

        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .stat-card { background: #182030; border: 1px solid #243049; border-radius: 8px; padding: 15px; text-align: center; }
        .stat-card h3 { font-size: 22px; color: #fff; margin-bottom: 4px; }
        .stat-card p { font-size: 12px; color: #94a3b8; text-transform: uppercase; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .panel { background: #182030; border: 1px solid #243049; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
        .panel h3 { color: #38bdf8; font-size: 16px; margin-bottom: 12px; }
        
        .verified-badge { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; background: #00a2ff; border-radius: 50%; color: white; font-size: 10px; margin-left: 5px; vertical-align: middle; }
        .tag { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 5px; text-transform: uppercase; }
        .tag-admin { background: #ef4444; color: white; }
        .tag-mod { background: #8b5cf6; color: white; }
        .tag-user { background: #3b82f6; color: white; }

        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
        .form-control { width: 100%; background: #131822; border: 1px solid #243049; padding: 10px; border-radius: 6px; color: #fff; font-size: 14px; }
        .checkbox-label { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; color: #cbd5e1; }

        .btn { display: block; width: 100%; padding: 12px; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; text-decoration: none; color: white; text-align: center; transition: 0.2s; }
        .btn-primary { background-color: #00a2ff; }
        .btn-primary:hover { background-color: #008be2; }
        .btn-google { background-color: #ea4335; }
        .btn-discord { background-color: #5865F2; }
        .btn-disabled { background-color: #1a2233; color: #55627a; text-decoration: line-through; cursor: not-allowed; border: 1px dashed #2a3852; font-size: 13px; }
        .btn-logout { background-color: #26171a; border: 1px solid #4a2228; color: #f87171; width: auto; padding: 6px 14px; font-size: 12px; }

        .center-box { text-align: center; max-width: 420px; margin: 40px auto; }
        .footer { margin-top: 20px; font-size: 11px; color: #475569; text-align: center; border-top: 1px solid #1f293d; padding-top: 15px; }
    </style>
</head>
<body>
    <div class="card">
        {% if user %}
            <div class="top-bar">
                <div class="brand">
                    <span>🚗 ФГУП «ГИБДД-РФ»</span>
                </div>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div class="online-status">
                        <div class="online-dot"></div> Онлайн
                    </div>
                    <a href="/logout" class="btn btn-logout">Выйти</a>
                </div>
            </div>

            <div class="nav-tabs">
                <button class="nav-btn active" onclick="switchTab('tab-main', this)">📊 Главная</button>
                <button class="nav-btn" onclick="switchTab('tab-cars', this)">🚗 ТС и Номера</button>
                <button class="nav-btn" onclick="switchTab('tab-users', this)">👥 Пользователи</button>
                {% if user.get('email') == 'danyasexual@gmail.com' %}
                <button class="nav-btn" onclick="switchTab('tab-settings', this)">⚙️ Кастомизация</button>
                {% endif %}
            </div>

            <div class="stats-grid">
                <div class="stat-card"><h3>142</h3><p>Номеров</p></div>
                <div class="stat-card"><h3>38</h3><p>Пользователей</p></div>
                <div class="stat-card"><h3>5</h3><p>Штрафов</p></div>
                <div class="stat-card"><h3>0</h3><p>В розыске</p></div>
            </div>

            <div id="tab-main" class="tab-content active">
                <div class="panel">
                    <h3>Профиль сотрудника / игрока</h3>
                    <p style="font-size: 14px; margin-bottom: 10px;">
                        <b>Имя:</b> {{ user.get('name') }} 
                        {% if user.get('verified') %}<span class="verified-badge" title="Верифицированный аккаунт">✓</span>{% endif %}
                    </p>
                    <p style="font-size: 13px; color: #94a3b8; margin-bottom: 10px;">
                        <b>Статус тегов:</b> 
                        {% if user.get('tags') %}
                            {% for t in user.get('tags') %}
                                {% if t == 'Руководство' %}<span class="tag tag-admin">Руководство</span>
                                {% elif t == 'Модератор' %}<span class="tag tag-mod">Модератор</span>
                                {% else %}<span class="tag tag-user">{{ t }}</span>{% endif %}
                            {% endfor %}
                        {% else %}
                            <span class="tag tag-user">Гражданин</span>
                        {% endif %}
                    </p>
                    <p style="font-size: 13px; color: #94a3b8;"><b>Авторизация через:</b> {{ user.get('provider') }}</p>
                </div>
                <div class="panel">
                    <h3>📋 Последние действия</h3>
                    <p style="color: #94a3b8; font-size: 13px;">Системный лог пуст. Все операции по выдаче блатных номеров и регистрации фиксируются автоматически.</p>
                </div>
            </div>

            <div id="tab-cars" class="tab-content">
                <div class="panel">
                    <h3>Биржа блатных номеров и ТС</h3>
                    <p style="color: #94a3b8; font-size: 13px; margin-bottom: 15px;">Управление государственными регистрационными знаками и транспортом.</p>
                    <button class="btn btn-primary" onclick="alert('Функционал добавления ТС активен!')">+ Зарегистрировать транспорт</button>
                </div>
            </div>

            <div id="tab-users" class="tab-content">
                <div class="panel">
                    <h3>Реестр игроков и сотрудников</h3>
                    <p style="color: #94a3b8; font-size: 13px;">Список активных учетных записей в базе данных ГИБДД.</p>
                </div>
            </div>

            {% if user.get('email') == 'danyasexual@gmail.com' %}
            <div id="tab-settings" class="tab-content">
                <div class="panel">
                    <h3>Панель кастомизации и верификации (Только для вас)</h3>
                    <form action="/update_settings" method="POST">
                        <div class="form-group">
                            <label>Выбрать должность / тег:</label>
                            <select name="tag" class="form-control">
                                <option value="Руководство" {% if 'Руководство' in user.get('tags', []) %}selected{% endif %}>Руководство</option>
                                <option value="Модератор" {% if 'Модератор' in user.get('tags', []) %}selected{% endif %}>Модератор</option>
                                <option value="Сотрудник" {% if 'Сотрудник' in user.get('tags', []) %}selected{% endif %}>Сотрудник ДПС</option>
                                <option value="Гражданин" {% if 'Гражданин' in user.get('tags', []) %}selected{% endif %}>Гражданин</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="checkbox-label">
                                <input type="checkbox" name="verified" value="true" {% if user.get('verified') %}checked{% endif %}>
                                Верифицировать аккаунт (Синяя галочка ✓)
                            </label>
                        </div>
                        <button type="submit" class="btn btn-primary">Сохранить изменения</button>
                    </form>
                </div>
            </div>
            {% endif %}

        {% else %}
            <div class="center-box">
                <h1 style="font-size: 20px; color: #fff; margin-bottom: 6px; text-transform: uppercase;">ФГУП «ГИБДД-РФ»</h1>
                <p style="font-size: 12px; color: #8a99ad; margin-bottom: 25px;">Портал авторизации и доступа к базе данных</p>
                <p style="margin-bottom: 15px; font-size: 14px; color: #94a3b8;">Авторизуйтесь для доступа:</p>
                <a href="/login/google" class="btn btn-google" style="margin-bottom: 10px;">Войти через Google</a>
                <a href="/login/discord" class="btn btn-discord" style="margin-bottom: 10px;">Войти через Discord (Beta)</a>
                <div class="btn btn-disabled">Войти через Roblox (Временно не работает)</div>
            </div>
        {% endif %}

        <div class="footer">ФГУП «ГИБДД-РФ» &copy; 2026. Официальный серверный реестр.</div>
    </div>

    <script>
        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
        }
    </script>
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
            sub = user_info.get('sub')
            email = user_info.get('email')
            db = load_db()
            user_key = f"google_{sub}"
            
            is_owner = (email == OWNER_EMAIL)
            existing = db.get(user_key, {})
            
            user_data = {
                'name': user_info.get('name'),
                'email': email,
                'provider': 'Google',
                'sub': sub,
                'tags': existing.get('tags', ['Руководство'] if is_owner else ['Гражданин']),
                'verified': existing.get('verified', True if is_owner else False)
            }
            session['user'] = user_data
            db[user_key] = user_data
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
            sub = user_info.get('id')
            email = user_info.get('email')
            db = load_db()
            user_key = f"discord_{sub}"
            
            username = f"{user_info.get('username')}#{user_info.get('discriminator', '0')}" if user_info.get('discriminator') and user_info.get('discriminator') != '0' else user_info.get('username')
            
            is_owner = (email == OWNER_EMAIL)
            existing = db.get(user_key, {})
            
            user_data = {
                'name': username,
                'email': email,
                'provider': 'Discord',
                'sub': sub,
                'tags': existing.get('tags', ['Руководство'] if is_owner else ['Гражданин']),
                'verified': existing.get('verified', True if is_owner else False)
            }
            session['user'] = user_data
            db[user_key] = user_data
            save_db(db)
    except Exception as e:
        print(f"Discord auth error: {e}")
    return redirect('/')

@app.route('/update_settings', methods=['POST'])
def update_settings():
    user = session.get('user')
    if not user or user.get('email') != OWNER_EMAIL:
        return redirect('/')
    
    selected_tag = request.form.get('tag', 'Руководство')
    is_verified = True if request.form.get('verified') == 'true' else False
    
    user['tags'] = [selected_tag]
    user['verified'] = is_verified
    session['user'] = user
    
    db = load_db()
    user_key = f"{user['provider'].lower()}_{user['sub']}"
    if user_key in db:
        db[user_key]['tags'] = user['tags']
        db[user_key]['verified'] = user['verified']
        save_db(db)
        
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

app = app
