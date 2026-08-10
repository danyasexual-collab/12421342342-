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
    <title>КАЛУГА РП / ФГУП «ГИБДД-РФ»</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #070a08; color: #c9d1d9; display: flex; min-height: 100vh; }
        
        /* Боковая панель */
        .sidebar { width: 240px; background-color: #050806; border-right: 1px solid #121e16; display: flex; flex-direction: column; justify-content: space-between; padding: 20px 15px; position: fixed; height: 100vh; overflow-y: auto; }
        .sidebar-brand { font-size: 16px; font-weight: bold; color: #22c55e; letter-spacing: 1px; margin-bottom: 25px; padding-left: 5px; }
        .nav-category { font-size: 10px; text-transform: uppercase; color: #4b5563; font-weight: bold; margin: 15px 0 6px 5px; letter-spacing: 0.5px; }
        .nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 12px; color: #9ca3af; text-decoration: none; border-radius: 6px; font-size: 13px; transition: 0.2s; margin-bottom: 3px; cursor: pointer; background: transparent; border: none; width: 100%; text-align: left; }
        .nav-item:hover, .nav-item.active { background-color: #0f1a13; color: #fff; }
        
        .user-mini { display: flex; align-items: center; gap: 10px; background: #0b120e; padding: 10px; border-radius: 8px; border: 1px solid #121e16; }
        .user-mini-avatar { width: 32px; height: 32px; background: #16241b; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #22c55e; font-size: 14px; }
        .user-mini-info { font-size: 12px; overflow: hidden; }
        .user-mini-info .name { color: #fff; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 130px; }
        .user-mini-info .sub { color: #6b7280; font-size: 10px; }

        /* Основной контент */
        .main-container { margin-left: 240px; flex: 1; display: flex; flex-direction: column; }
        
        /* Верхняя бегущая строка */
        .top-marquee { background-color: #090f0b; border-bottom: 1px solid #121e16; padding: 8px 20px; font-size: 11px; color: #6b7280; white-space: nowrap; overflow: hidden; }
        
        /* Верхние быстрые карточки */
        .top-cards-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; padding: 15px 20px; background-color: #070a08; border-bottom: 1px solid #121e16; }
        .top-card-item { background: #0b120e; border: 1px solid #142218; padding: 10px; border-radius: 6px; text-align: center; text-decoration: none; color: #9ca3af; font-size: 11px; transition: 0.2s; }
        .top-card-item:hover { border-color: #22c55e; color: #fff; }
        .top-card-item b { display: block; font-size: 12px; color: #fff; margin-bottom: 2px; text-transform: uppercase; }

        /* Контентная область */
        .content-body { padding: 25px; flex: 1; }
        
        .page-title { font-size: 20px; font-weight: bold; color: #fff; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
        .page-subtitle { font-size: 12px; color: #6b7280; margin-bottom: 20px; }

        /* Статистика */
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .stat-box { background: #0b120e; border: 1px solid #121e16; border-radius: 8px; padding: 18px; text-align: center; }
        .stat-box h3 { font-size: 24px; color: #fff; font-weight: bold; margin-bottom: 4px; }
        .stat-box p { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }

        /* Панели и вкладки */
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .panel { background: #0b120e; border: 1px solid #121e16; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
        .panel h3 { color: #fff; font-size: 15px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        .panel p { font-size: 13px; color: #9ca3af; line-height: 1.5; }

        /* Бейджи и теги */
        .verified-badge { display: inline-flex; align-items: center; justify-content: center; width: 15px; height: 15px; background: #00a2ff; border-radius: 50%; color: white; font-size: 9px; margin-left: 4px; vertical-align: middle; }
        .tag { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: bold; margin-right: 5px; text-transform: uppercase; }
        .tag-admin { background: #dc2626; color: white; }
        .tag-mod { background: #7c3aed; color: white; }
        .tag-user { background: #2563eb; color: white; }

        /* Формы */
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 12px; color: #9ca3af; margin-bottom: 5px; }
        .form-control { width: 100%; background: #070a08; border: 1px solid #142218; padding: 9px 12px; border-radius: 6px; color: #fff; font-size: 13px; }
        .checkbox-label { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; color: #d1d5db; }

        .btn { display: inline-block; padding: 10px 16px; border: none; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer; text-decoration: none; color: white; text-align: center; transition: 0.2s; }
        .btn-green { background-color: #166534; color: #fff; }
        .btn-green:hover { background-color: #15803d; }
        .btn-dark { background-color: #111827; border: 1px solid #1f2937; color: #9ca3af; }
        .btn-dark:hover { background-color: #1f2937; color: #fff; }
        .btn-google { background-color: #dc2626; width: 100%; margin-bottom: 8px; }
        .btn-discord { background-color: #4f46e5; width: 100%; margin-bottom: 8px; }
        .btn-disabled { background-color: #0f1411; color: #4b5563; text-decoration: line-through; cursor: not-allowed; border: 1px dashed #1a2c1f; width: 100%; font-size: 12px; }

        .auth-card { background: #0b120e; border: 1px solid #121e16; border-radius: 10px; max-width: 400px; margin: 60px auto; padding: 30px; text-align: center; }
    </style>
</head>
<body>

    {% if user %}
    <!-- Боковое меню -->
    <div class="sidebar">
        <div>
            <div class="sidebar-brand">КАЛУГА РП</div>
            
            <div class="nav-category">Основное</div>
            <button class="nav-item active" onclick="switchTab('tab-main', this)">🏠 Главная</button>
            <button class="nav-item" onclick="switchTab('tab-forum', this)">💬 Форум</button>
            
            <div class="nav-category">Важное</div>
            <button class="nav-item" onclick="switchTab('tab-status', this)">🟢 Статус сервера</button>
            <button class="nav-item" onclick="switchTab('tab-rules', this)">📜 Правила</button>
            <button class="nav-item" onclick="switchTab('tab-mod', this)">🛡️ Набор на модерацию</button>
            <button class="nav-item" onclick="switchTab('tab-messages', this)">✉️ Сообщения</button>
            <button class="nav-item" onclick="switchTab('tab-users', this)">👥 Участники</button>
            <button class="nav-item" onclick="switchTab('tab-reviews', this)">⭐ Отзывы о сотрудниках</button>

            <div class="nav-category">Интересное</div>
            <button class="nav-item" onclick="switchTab('tab-shop', this)">🛒 Магазин</button>
            <button class="nav-item" onclick="switchTab('tab-tasks', this)">🎯 Задания</button>
            
            {% if user.get('email') == 'danyasexual@gmail.com' %}
            <div class="nav-category">Администрирование</div>
            <button class="nav-item" onclick="switchTab('tab-settings', this)">⚙️ Кастомизация</button>
            {% endif %}
        </div>

        <div>
            <div class="user-mini">
                <div class="user-mini-avatar">{{ user.get('name')[0] | upper }}</div>
                <div class="user-mini-info">
                    <div class="name">{{ user.get('name') }}</div>
                    <div class="sub">{{ user.get('provider') }}</div>
                </div>
            </div>
            <a href="/logout" class="btn btn-dark" style="width: 100%; margin-top: 10px; padding: 7px; font-size: 11px;">Выйти из системы</a>
        </div>
    </div>

    <!-- Основной блок справа -->
    <div class="main-container">
        <div class="top-marquee">
            ДОБРО ПОЖАЛОВАТЬ НА КАЛУГА РП! • СЛЕДИ ЗА АНОНСАМИ • ФГУП «ГИБДД-РФ» ОФИЦИАЛЬНЫЙ ПОРТАЛ • НАБОР В СОТРУДНИКИ ОТКРЫТ
        </div>

        <div class="top-cards-grid">
            <a href="#" class="top-card-item" onclick="switchTab('tab-forum', document.querySelectorAll('.nav-item')[1]); return false;"><b>Новости</b>Последние анонсы</a>
            <a href="https://discord.com" target="_blank" class="top-card-item"><b>Discord</b>Войти в сервер</a>
            <a href="#" class="top-card-item" onclick="switchTab('tab-shop', document.querySelectorAll('.nav-item')[9]); return false;"><b>Магазин</b>Рамки и фоны</a>
            <a href="#" class="top-card-item" onclick="switchTab('tab-main', document.querySelectorAll('.nav-item')[0]); return false;"><b>Фракции</b>ГУМВД / ГИБДД</a>
            <a href="#" class="top-card-item" onclick="switchTab('tab-messages', document.querySelectorAll('.nav-item')[5]); return false;"><b>Поддержка</b>Создать тикет</a>
            <a href="https://telegram.org" target="_blank" class="top-card-item"><b>Telegram</b>Канал связи</a>
            <a href="#" class="top-card-item" onclick="switchTab('tab-rules', document.querySelectorAll('.nav-item')[3]); return false;"><b>Правила</b>Читать правила</a>
        </div>

        <div class="content-body">
            <!-- Вкладка: Главная -->
            <div id="tab-main" class="tab-content active">
                <div class="page-title">Калуга РП</div>
                <div class="page-subtitle">Официальный форум и единый портал ГИБДД-РФ</div>

                <div class="stats-grid">
                    <div class="stat-box">
                        <h3>21</h3>
                        <p>Игроков</p>
                    </div>
                    <div class="stat-box">
                        <h3>1</h3>
                        <p>Онлайн</p>
                    </div>
                    <div class="stat-box">
                        <h3>1</h3>
                        <p>Постов</p>
                    </div>
                    <div class="stat-box">
                        <h3>2026</h3>
                        <p>Основан</p>
                    </div>
                </div>

                <div class="panel">
                    <h3>👤 Информация о вашем аккаунте</h3>
                    <p style="margin-bottom: 6px;"><b>Имя:</b> {{ user.get('name') }} {% if user.get('verified') %}<span class="verified-badge" title="Верифицирован">✓</span>{% endif %}</p>
                    <p style="margin-bottom: 6px;"><b>Должность / Тег:</b> 
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
                    <p><b>Способ авторизации:</b> {{ user.get('provider') }}</p>
                </div>
            </div>

            <!-- Вкладка: Форум -->
            <div id="tab-forum" class="tab-content">
                <div class="page-title">Форум проекта</div>
                <div class="page-subtitle">Обсуждения, новости и регламенты</div>
                <div class="panel">
                    <h3>Последние анонсы</h3>
                    <p>Раздел находится в разработке. Скорее всего здесь появятся темы по обмену блатных номеров и регистрации автотранспорта.</p>
                </div>
            </div>

            <!-- Вкладка: Статус -->
            <div id="tab-status" class="tab-content">
                <div class="page-title">Статус сервера</div>
                <div class="page-subtitle">Мониторинг работоспособности узлов</div>
                <div class="panel">
                    <h3>🟢 Все системы функционируют штатно</h3>
                    <p>Игровой сервер и база данных ГИБДД работают без задержек.</p>
                </div>
            </div>

            <!-- Вкладка: Правила -->
            <div id="tab-rules" class="tab-content">
                <div class="page-title">Правила сервера</div>
                <div class="page-subtitle">Обязательно к ознакомлению</div>
                <div class="panel">
                    <h3>Регламент поведения</h3>
                    <p>1. Соблюдайте ролевой процесс (RP).<br>2. Запрещено использование стороннего ПО.<br>3. Уважительно относитесь к руководству.</p>
                </div>
            </div>

            <!-- Вкладка: Набор на модерацию -->
            <div id="tab-mod" class="tab-content">
                <div class="page-title">Набор на модерацию</div>
                <div class="page-subtitle">Стань частью команды проекта</div>
                <div class="panel">
                    <h3>Анкета кандидата</h3>
                    <p>Набор временно закрыт. Следите за новостями в Discord канале.</p>
                </div>
            </div>

            <!-- Вкладка: Сообщения -->
            <div id="tab-messages" class="tab-content">
                <div class="page-title">Сообщения</div>
                <div class="page-subtitle">Ваши личные диалоги и уведомления</div>
                <div class="panel">
                    <h3>Входящие</h3>
                    <p>У вас нет новых системных уведомлений.</p>
                </div>
            </div>

            <!-- Вкладка: Участники -->
            <div id="tab-users" class="tab-content">
                <div class="page-title">Участники</div>
                <div class="page-subtitle">Зарегистрированные игроки</div>
                <div class="panel">
                    <h3>Список пользователей</h3>
                    <p>База данных насчитывает активных участников ролевого проекта.</p>
                </div>
            </div>

            <!-- Вкладка: Отзывы -->
            <div id="tab-reviews" class="tab-content">
                <div class="page-title">Отзывы о сотрудниках</div>
                <div class="page-subtitle">Оценка работы личного состава</div>
                <div class="panel">
                    <h3>Книга жалоб и предложений</h3>
                    <p>Здесь вы можете оставить отзыв о работе сотрудников ДПС ГИБДД.</p>
                </div>
            </div>

            <!-- Вкладка: Магазин -->
            <div id="tab-shop" class="tab-content">
                <div class="page-title">Магазин</div>
                <div class="page-subtitle">Рамки, фоны и блатные номера</div>
                <div class="panel">
                    <h3>Эксклюзивные предложения</h3>
                    <p>Раздел покупки уникальных цифровых знаков для автомобилей.</p>
                </div>
            </div>

            <!-- Вкладка: Задания -->
            <div id="tab-tasks" class="tab-content">
                <div class="page-title">Задания</div>
                <div class="page-subtitle">Ежедневные квесты и награды</div>
                <div class="panel">
                    <h3>Активные миссии</h3>
                    <p>Патрулируйте область, выписывайте штрафы и получайте бонусы.</p>
                </div>
            </div>

            {% if user.get('email') == 'danyasexual@gmail.com' %}
            <!-- Вкладка: Кастомизация (Только для тебя) -->
            <div id="tab-settings" class="tab-content">
                <div class="page-title">Панель управления</div>
                <div class="page-subtitle">Кастомизация профиля и прав администратора</div>
                <div class="panel">
                    <h3>Настройка тегов и галочки</h3>
                    <form action="/update_settings" method="POST">
                        <div class="form-group">
                            <label>Выберите тег / должность:</label>
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
                        <button type="submit" class="btn btn-green">Сохранить изменения</button>
                    </form>
                </div>
            </div>
            {% endif %}
        </div>
    </div>

    {% else %}
    <!-- Экран авторизации -->
    <div style="width: 100%; display: flex; justify-content: center; align-items: center; min-height: 100vh;">
        <div class="auth-card">
            <h1 style="font-size: 20px; color: #fff; margin-bottom: 6px; text-transform: uppercase;">КАЛУГА РП</h1>
            <p style="font-size: 12px; color: #6b7280; margin-bottom: 25px;">Авторизация для доступа к порталу</p>
            <a href="/login/google" class="btn btn-google">Войти через Google</a>
            <a href="/login/discord" class="btn btn-discord">Войти через Discord (Beta)</a>
            <div class="btn btn-disabled">Войти через Roblox (Временно не работает)</div>
        </div>
    </div>
    {% endif %}

    <script>
        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            if(btn) btn.classList.add('active');
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
