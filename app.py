# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import json
import os
import datetime
import random

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dps-dev-key-change-in-prod')

DATA_FILE = 'database.json'

# --- НАСТРОЙКА OAUTH (АВТОМАТИЧЕСКИЙ DISCOVERY) ---
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

roblox = oauth.register(
    name='roblox',
    client_id=os.environ.get('ROBLOX_CLIENT_ID', 'YOUR_ROBLOX_CLIENT_ID'),
    client_secret=os.environ.get('ROBLOX_CLIENT_SECRET', 'YOUR_ROBLOX_CLIENT_SECRET'),
    server_metadata_url='https://apis.roblox.com/oauth/v1/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile'}
)


# --- ХРАНИЛИЩЕ ---

def load_db():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "accounts": [
                {
                    "email": "admin@dps.gov",
                    "username": "Creator",
                    "password": generate_password_hash("admin123"),
                    "provider": "local"
                }
            ],
            "pending_codes": {},
            "plates": [],
            "fines": [],
            "history": [],
            "auction": {
                "plate": "Ожидание лота",
                "price": 0,
                "seller": "—",
                "highest_bidder": "Отсутствует",
                "active": False
            },
            "logs": [
                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Система запущена"
            ]
        }
        save_db(default_data)
        return default_data
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_log(db, text):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db["logs"].insert(0, f"{now} — {text}")
    db["logs"] = db["logs"][:30]


# --- OAuth МАРШРУТЫ ---

@app.route('/auth/google')
def login_google():
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if not user_info:
        return redirect('/')

    email = user_info['email'].lower()
    username = user_info.get('name', email.split('@')[0])

    db = load_db()
    account = next((acc for acc in db['accounts'] if acc['email'] == email), None)

    if not account:
        account = {
            "email": email,
            "username": username,
            "provider": "google"
        }
        db['accounts'].append(account)
        add_log(db, f"Регистрация через Google: {username}")
    else:
        add_log(db, f"Вход через Google: {username}")

    save_db(db)
    session['user_email'] = email
    return redirect('/')


@app.route('/auth/roblox')
def login_roblox():
    redirect_uri = url_for('auth_roblox_callback', _external=True)
    return roblox.authorize_redirect(redirect_uri)

@app.route('/auth/roblox/callback')
def auth_roblox_callback():
    token = roblox.authorize_access_token()
    user_info = roblox.userinfo(token=token)
    if not user_info:
        return redirect('/')

    roblox_id = user_info['sub']
    username = user_info.get('preferred_username', f"Roblox_{roblox_id}")
    fake_email = f"roblox_{roblox_id}@roblox.local"

    db = load_db()
    account = next((acc for acc in db['accounts'] if acc.get('roblox_id') == roblox_id), None)

    if not account:
        account = {
            "email": fake_email,
            "username": username,
            "roblox_id": roblox_id,
            "provider": "roblox"
        }
        db['accounts'].append(account)
        add_log(db, f"Регистрация через Roblox: {username}")
    else:
        add_log(db, f"Вход через Roblox: {username}")

    save_db(db)
    session['user_email'] = account['email']
    return redirect('/')


# --- ЛОКАЛЬНАЯ АВТОРИЗАЦИЯ И КОДЫ ПОЧТЫ ---

@app.route('/api/register/send-code', methods=['POST'])
def register_send_code():
    db = load_db()
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not email or not username or not password:
        return jsonify({"error": "Заполните все поля"}), 400

    if any(acc['email'] == email for acc in db['accounts']):
        return jsonify({"error": "Пользователь с такой почтой уже существует"}), 400

    code = f"{random.randint(100000, 999999)}"
    db['pending_codes'][email] = {
        "code": code,
        "username": username,
        "password": generate_password_hash(password)
    }
    
    # В консоль сервера выводится код для локального теста
    print(f"\n========================================\n[КОД ПОДТВЕРЖДЕНИЯ ДЛЯ {email}]: {code}\n========================================\n")
    
    add_log(db, f"Сгенерирован код для {email}")
    save_db(db)
    return jsonify({"success": True, "message": "Код отправлен (проверьте консоль сервера)"})

@app.route('/api/register/confirm', methods=['POST'])
def register_confirm():
    db = load_db()
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()

    pending = db['pending_codes'].get(email)
    if not pending or pending['code'] != code:
        return jsonify({"error": "Неверный код"}), 400

    new_account = {
        "email": email,
        "username": pending['username'],
        "password": pending['password'],
        "provider": "local"
    }

    db['accounts'].append(new_account)
    del db['pending_codes'][email]
    add_log(db, f"Новый аккаунт подтвержден: {new_account['username']}")
    save_db(db)

    session['user_email'] = email
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def login():
    db = load_db()
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    account = next((acc for acc in db['accounts'] if acc['email'] == email), None)

    if not account or account.get('provider') != 'local' or not check_password_hash(account.get('password', ''), password):
        return jsonify({"error": "Неверный логин или пароль"}), 400

    session['user_email'] = account['email']
    add_log(db, f"Вход: {account['username']}")
    save_db(db)
    return jsonify({"success": True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/me')
def get_me():
    email = session.get('user_email')
    if not email:
        return jsonify(None), 401

    db = load_db()
    account = next((acc for acc in db['accounts'] if acc['email'] == email), None)
    if not account:
        return jsonify(None), 401

    return jsonify({
        "email": account['email'],
        "username": account['username'],
        "provider": account.get('provider', 'local')
    })


# --- API СИСТЕМЫ ---

def require_auth():
    if 'user_email' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return None

@app.route('/api/stats')
def get_stats():
    err = require_auth()
    if err: return err
    db = load_db()
    return jsonify({
        "total_plates": len(db['plates']),
        "total_users": len(db['accounts']),
        "total_fines": len(db['fines']),
        "total_wanted": sum(1 for p in db['plates'] if p['wanted']),
        "logs": db['logs']
    })

@app.route('/api/plates')
def get_plates():
    err = require_auth()
    if err: return err
    return jsonify(load_db()['plates'])

@app.route('/api/fines')
def get_fines():
    err = require_auth()
    if err: return err
    return jsonify(load_db()['fines'])

@app.route('/api/auction')
def get_auction():
    err = require_auth()
    if err: return err
    return jsonify(load_db()['auction'])

@app.route('/api/give', methods=['POST'])
def give_plate():
    err = require_auth()
    if err: return err
    db = load_db()
    data = request.json or {}
    plate_num = data.get('plate', '').strip().upper()
    owner = data.get('owner', '').strip()
    
    if not plate_num or not owner:
        return jsonify({"error": "Заполните данные"}), 400

    db['plates'].append({
        "plate": plate_num,
        "owner": owner,
        "price": int(data.get('price') or 15000),
        "rarity": data.get('rarity', 'Обычный'),
        "wanted": False
    })
    add_log(db, f"Выдан номер [{plate_num}] -> {owner}")
    save_db(db)
    return jsonify({"success": True})


# --- ИНТЕРФЕЙС ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>База ДПС</title>
    <style>
        :root {
            --bg: #090d16;
            --panel: #111827;
            --border: #1f2937;
            --text: #f3f4f6;
            --muted: #9ca3af;
            --accent: #f59e0b;
            --red: #ef4444;
            --green: #10b981;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
        body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }

        /* Экран входа */
        .auth-screen {
            position: fixed; inset: 0; background: rgba(9, 13, 22, 0.98);
            display: flex; align-items: center; justify-content: center; z-index: 100;
        }
        .auth-card {
            background: var(--panel); border: 1px solid var(--border);
            padding: 2rem; border-radius: 12px; width: 100%; max-width: 400px;
        }
        .auth-title { font-size: 1.5rem; font-weight: 700; color: var(--accent); text-align: center; margin-bottom: 1.5rem; }

        .btn-oauth {
            display: flex; align-items: center; justify-content: center; gap: 10px;
            width: 100%; padding: 10px; border-radius: 6px; border: none; font-weight: 600;
            cursor: pointer; text-decoration: none; color: #fff; margin-bottom: 8px; font-size: 0.9rem;
        }
        .btn-google { background: #4285F4; }
        .btn-roblox { background: #00A2FF; }

        .divider { text-align: center; color: var(--muted); margin: 1rem 0; font-size: 0.8rem; }

        input {
            width: 100%; background: var(--bg); border: 1px solid var(--border);
            color: var(--text); padding: 10px; border-radius: 6px; margin-bottom: 10px; outline: none;
        }
        input:focus { border-color: var(--accent); }

        .btn {
            background: #2563eb; color: #fff; border: none; padding: 10px 16px;
            border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.9rem;
        }
        .btn-gold { background: var(--accent); color: #000; font-weight: 600; width: 100%; }

        /* Основной интерфейс */
        #app { display: none; flex-direction: column; flex: 1; }
        header { background: var(--panel); border-bottom: 1px solid var(--border); padding: 1rem 2rem; display: flex; justify-content: space-between; }
        main { padding: 2rem; max-width: 1200px; margin: 0 auto; width: 100%; }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { background: var(--panel); border: 1px solid var(--border); padding: 1.5rem; border-radius: 8px; }
        .val { font-size: 1.8rem; font-weight: bold; color: var(--accent); margin-top: 0.5rem; }

        .logs { background: var(--panel); border: 1px solid var(--border); padding: 1rem; border-radius: 8px; font-family: monospace; max-height: 250px; overflow-y: auto; }
        .log-item { padding: 4px 0; border-bottom: 1px solid var(--border); color: var(--muted); font-size: 0.85rem; }
    </style>
</head>
<body>

    <div class="auth-screen" id="auth-screen">
        <div class="auth-card">
            <div class="auth-title">🚨 БАЗА ДПС</div>

            <a href="/auth/google" class="btn-oauth btn-google">Войти через Google</a>
            <a href="/auth/roblox" class="btn-oauth btn-roblox">Войти через Roblox</a>

            <div class="divider">или через Email</div>

            <div id="login-form">
                <input type="email" id="email" placeholder="Email">
                <input type="password" id="pass" placeholder="Пароль">
                <button class="btn btn-gold" onclick="login()">Войти</button>
                <div style="text-align: center; margin-top: 10px;">
                    <a href="#" onclick="toggleAuthMode()" style="color: var(--muted); font-size: 0.8rem;">Нет аккаунта? Регистрация</a>
                </div>
            </div>

            <div id="reg-form" style="display: none;">
                <input type="text" id="reg-user" placeholder="Имя пользователя">
                <input type="email" id="reg-email" placeholder="Email">
                <input type="password" id="reg-pass" placeholder="Пароль">
                <button class="btn btn-gold" onclick="sendCode()">Запросить код</button>
            </div>

            <div id="code-form" style="display: none;">
                <input type="text" id="code" placeholder="Код из консоли">
                <button class="btn btn-gold" onclick="confirmCode()">Подтвердить</button>
            </div>
        </div>
    </div>

    <div id="app">
        <header>
            <div style="font-weight: bold; color: var(--accent);">🚨 ДПС СИСТЕМА</div>
            <div style="display: flex; align-items: center; gap: 15px;">
                <span id="user-display"></span>
                <a href="/logout" style="color: var(--red); text-decoration: none; font-size: 0.85rem;">Выйти</a>
            </div>
        </header>
        <main>
            <div class="grid">
                <div class="card">Всего номеров <div class="val" id="st-plates">0</div></div>
                <div class="card">Пользователей <div class="val" id="st-users">0</div></div>
                <div class="card">Штрафов <div class="val" id="st-fines">0</div></div>
            </div>
            <h3>Логи системы</h3>
            <div class="logs" id="logs"></div>
        </main>
    </div>

    <script>
        async function checkAuth() {
            const res = await fetch('/api/me');
            if (res.ok) {
                const user = await res.json();
                document.getElementById('auth-screen').style.display = 'none';
                document.getElementById('app').style.display = 'flex';
                document.getElementById('user-display').innerText = `${user.username} (${user.provider})`;
                loadStats();
            }
        }

        async function login() {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: document.getElementById('email').value,
                    password: document.getElementById('pass').value
                })
            });
            if (res.ok) checkAuth();
            else alert((await res.json()).error);
        }

        function toggleAuthMode() {
            document.getElementById('login-form').style.display = 'none';
            document.getElementById('reg-form').style.display = 'block';
        }

        async function sendCode() {
            const res = await fetch('/api/register/send-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: document.getElementById('reg-user').value,
                    email: document.getElementById('reg-email').value,
                    password: document.getElementById('reg-pass').value
                })
            });
            if (res.ok) {
                document.getElementById('reg-form').style.display = 'none';
                document.getElementById('code-form').style.display = 'block';
            } else alert((await res.json()).error);
        }

        async function confirmCode() {
            const res = await fetch('/api/register/confirm', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: document.getElementById('reg-email').value,
                    code: document.getElementById('code').value
                })
            });
            if (res.ok) checkAuth();
            else alert((await res.json()).error);
        }

        async function loadStats() {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const data = await res.json();
            document.getElementById('st-plates').innerText = data.total_plates;
            document.getElementById('st-users').innerText = data.total_users;
            document.getElementById('st-fines').innerText = data.total_fines;
            document.getElementById('logs').innerHTML = data.logs.map(l => `<div class="log-item">${l}</div>`).join('');
        }

        checkAuth();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True, port=5000)