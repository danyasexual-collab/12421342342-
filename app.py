import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gibdd_rf_secret_key_super_secure")

# Настройка OAuth через Authlib
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Vercel имеет доступ к файловой системе только для чтения, кроме /tmp
DB_PATH = "/tmp/gibdd.db" if os.environ.get("VERCEL") else "gibdd.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_email TEXT UNIQUE,
            google_name TEXT,
            roblox_nick TEXT,
            ic_name TEXT,
            age INTEGER,
            job TEXT,
            registered INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT,
            owner_ic TEXT,
            is_special INTEGER,
            price INTEGER,
            status TEXT DEFAULT 'Свободен'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ic_name TEXT,
            amount INTEGER,
            reason TEXT,
            status TEXT DEFAULT 'Не оплачен'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wanted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ic_name TEXT,
            reason TEXT,
            level TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM plates")
    if cursor.fetchone()[0] == 0:
        sample_plates = [
            ("А777АА 77", "Государственный фонд", 1, 500000),
            ("В001ОР 99", "Государственный фонд", 1, 350000),
            ("М333ММ 777", "Государственный фонд", 1, 400000),
            ("К123ОР 50", "Государственный фонд", 0, 50000),
            ("Х456ТТ 78", "Государственный фонд", 0, 45000),
        ]
        cursor.executemany("INSERT INTO plates (plate_number, owner_ic, is_special, price, status) VALUES (?, ?, ?, ?, 'Свободен')", sample_plates)
    
    cursor.execute("SELECT COUNT(*) FROM wanted")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO wanted (ic_name, reason, level) VALUES (?, ?, ?)", ("Иван Иванов", "Угон патрульного авто ФГУП", "Высокий"))

    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ФГУП "ГИБДД-РФ" | Портал</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
    <header class="bg-slate-900 border-b border-slate-800 shadow-lg">
        <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <div class="bg-blue-600 text-white font-black px-3 py-1.5 rounded-lg tracking-wider text-lg shadow-md border border-blue-400">ГИБДД-РФ</div>
                <span class="text-xs uppercase tracking-widest text-slate-400 font-semibold hidden sm:inline">Федеральное государственное унитарное предприятие</span>
            </div>
            <div class="flex items-center space-x-4">
                {% if 'user' in session %}
                    <span class="text-sm text-slate-300">👤 {{ session['user'] }}</span>
                    <a href="/logout" class="bg-red-600 hover:bg-red-700 px-3 py-1.5 rounded text-sm transition">Выйти</a>
                {% else %}
                    <a href="/login-google" class="bg-white text-slate-900 hover:bg-slate-200 px-4 py-2 rounded font-medium text-sm flex items-center space-x-2 transition shadow">
                        <span>Войти через Google</span>
                    </a>
                {% endif %}
            </div>
        </div>
    </header>

    <div class="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="md:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl h-fit">
            <h2 class="text-xs uppercase tracking-wider text-slate-400 font-bold mb-3 px-2">Меню управления</h2>
            <nav class="space-y-1">
                <a href="/" class="block px-3 py-2 rounded-lg text-sm transition {% if active == 'home' %}bg-blue-600 text-white font-medium{% else %}hover:bg-slate-800 text-slate-300{% endif %}">Главная</a>
                <a href="/register-char" class="block px-3 py-2 rounded-lg text-sm transition {% if active == 'register' %}bg-blue-600 text-white font-medium{% else %}hover:bg-slate-800 text-slate-300{% endif %}">Профиль персонажа</a>
                
                {% if session.get('registered') %}
                    <a href="/plates" class="block px-3 py-2 rounded-lg text-sm transition {% if active == 'plates' %}bg-blue-600 text-white font-medium{% else %}hover:bg-slate-800 text-slate-300{% endif %}">Гос. номера и Блатные</a>
                    <a href="/fines" class="block px-3 py-2 rounded-lg text-sm transition {% if active == 'fines' %}bg-blue-600 text-white font-medium{% else %}hover:bg-slate-800 text-slate-300{% endif %}">Штрафы</a>
                    <a href="/wanted" class="block px-3 py-2 rounded-lg text-sm transition {% if active == 'wanted' %}bg-blue-600 text-white font-medium{% else %}hover:bg-slate-800 text-slate-300{% endif %}">База розыска</a>
                {% else %}
                    <div class="pt-4 mt-4 border-t border-slate-800 px-2">
                        <p class="text-xs text-amber-400 bg-amber-950/40 p-2.5 rounded border border-amber-800/50 leading-relaxed">
                            ⚠️ 90% функций заблокировано. Заполните профиль персонажа, чтобы разблокировать доступ.
                        </p>
                    </div>
                {% endif %}
            </nav>
        </div>

        <div class="md:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            {% if active == 'home' %}
                <h1 class="text-2xl font-bold mb-4">Официальный портал ФГУП «ГИБДД-РФ»</h1>
                <p class="text-slate-300 leading-relaxed mb-6">Добро пожаловать в единую информационную систему распределения автомобильных номеров, учета штрафов и контроля транспортной безопасности.</p>
                
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                    <div class="bg-slate-950 p-4 rounded-lg border border-slate-800">
                        <div class="text-2xl font-bold text-blue-500">🚗 Госреестр</div>
                        <div class="text-xs text-slate-400 mt-1">Распределение стандартных и блатных номерных знаков.</div>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-lg border border-slate-800">
                        <div class="text-2xl font-bold text-amber-500">📜 Штрафы</div>
                        <div class="text-xs text-slate-400 mt-1">Автоматическая фиксация и оплата правонарушений.</div>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-lg border border-slate-800">
                        <div class="text-2xl font-bold text-red-500">🚨 Розыск</div>
                        <div class="text-xs text-slate-400 mt-1">Оперативная база данных угнанных авто и граждан.</div>
                    </div>
                </div>

                {% if not session.get('user') %}
                    <div class="bg-blue-950/30 border border-blue-900/50 p-4 rounded-lg flex items-center justify-between">
                        <div>
                            <h3 class="font-semibold text-blue-400">Требуется авторизация</h3>
                            <p class="text-xs text-slate-400 mt-0.5">Войдите через аккаунт Google для начала работы в системе.</p>
                        </div>
                        <a href="/login-google" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition">Войти</a>
                    </div>
                {% endif %}

            {% elif active == 'register' %}
                <h1 class="text-2xl font-bold mb-4">Регистрация персонажа</h1>
                <p class="text-xs text-slate-400 mb-6">Вы можете пропустить этот шаг, но 90% функций портала останутся недоступными.</p>
                
                <form method="POST" action="/register-char" class="space-y-4 max-w-lg">
                    <div>
                        <label class="block text-xs uppercase font-semibold text-slate-400 mb-1">Ник в Roblox</label>
                        <input type="text" name="roblox_nick" value="{{ user_data[3] if user_data else '' }}" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <div>
                        <label class="block text-xs uppercase font-semibold text-slate-400 mb-1">ФИО IC (Игровое)</label>
                        <input type="text" name="ic_name" value="{{ user_data[4] if user_data else '' }}" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <div>
                        <label class="block text-xs uppercase font-semibold text-slate-400 mb-1">Возраст</label>
                        <input type="number" name="age" value="{{ user_data[5] if user_data else '' }}" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <div>
                        <label class="block text-xs uppercase font-semibold text-slate-400 mb-1">Место работы</label>
                        <input type="text" name="job" value="{{ user_data[6] if user_data else '' }}" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <div class="flex space-x-3 pt-2">
                        <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition shadow">Сохранить и активировать</button>
                        <a href="/" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg text-sm font-medium transition flex items-center">Пропустить</a>
                    </div>
                </form>

            {% elif active == 'plates' %}
                <h1 class="text-2xl font-bold mb-4">Распределение и магазин гос. номеров</h1>
                <p class="text-xs text-slate-400 mb-6">Получите стандартный номер или приобретите уникальный «блатнной» госзнак.</p>
                
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm text-slate-300">
                        <thead class="bg-slate-950 text-xs uppercase text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="p-3">Номер</th>
                                <th class="p-3">Тип</th>
                                <th class="p-3">Цена</th>
                                <th class="p-3">Статус</th>
                                <th class="p-3 text-right">Действие</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            {% for plate in plates %}
                            <tr class="hover:bg-slate-950/40">
                                <td class="p-3 font-mono font-bold text-white bg-slate-950/65 rounded border border-slate-800 my-1 inline-block">{{ plate[1] }}</td>
                                <td class="p-3">{% if plate[3] %}🔥 Блатной{% else %}Обычный{% endif %}</td>
                                <td class="p-3 font-semibold text-emerald-400">{{ plate[4] }} ₽</td>
                                <td class="p-3"><span class="px-2 py-0.5 rounded text-xs {% if plate[5] == 'Занят' %}bg-red-950 text-red-400 border border-red-900{% else %}bg-emerald-950 text-emerald-400 border border-emerald-900{% endif %}">{{ plate[5] }}</span></td>
                                <td class="p-3 text-right">
                                    {% if plate[5] == 'Свободен' %}
                                        <form method="POST" action="/buy-plate/{{ plate[0] }}">
                                            <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs transition">Получить / Купить</button>
                                        </form>
                                    {% else %}
                                        <span class="text-xs text-slate-500">Занято</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

            {% elif active == 'fines' %}
                <h1 class="text-2xl font-bold mb-4">База штрафов</h1>
                <p class="text-xs text-slate-400 mb-6">Список ваших зафиксированных правонарушений.</p>
                
                <div class="space-y-3">
                    {% for fine in fines %}
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-lg flex justify-between items-center">
                        <div>
                            <div class="text-sm font-semibold text-white">{{ fine[2] }} ₽ — <span class="text-slate-400">{{ fine[3] }}</span></div>
                            <div class="text-xs text-slate-500 mt-0.5">Статус: <span class="text-amber-400">{{ fine[4] }}</span></div>
                        </div>
                        {% if fine[4] == 'Не оплачен' %}
                        <form method="POST" action="/pay-fine/{{ fine[0] }}">
                            <button type="submit" class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded text-xs transition font-medium">Оплатить</button>
                        </form>
                        {% else %}
                        <span class="text-xs text-emerald-500 font-medium">Оплачено</span>
                        {% endif %}
                    </div>
                    {% else %}
                    <p class="text-sm text-slate-400">У вас нет активных штрафов. Отличная езда!</p>
                    {% endfor %}
                </div>

            {% elif active == 'wanted' %}
                <h1 class="text-2xl font-bold mb-4">Федеральный розыск</h1>
                <p class="text-xs text-slate-400 mb-6">Список лиц и транспортных средств, находящихся в розыске ФГУП «ГИБДД-РФ».</p>
                
                <div class="space-y-3">
                    {% for person in wanted %}
                    <div class="bg-red-950/20 border border-red-900/40 p-4 rounded-lg flex justify-between items-center">
                        <div>
                            <div class="text-sm font-bold text-white">{{ person[1] }}</div>
                            <div class="text-xs text-slate-400 mt-0.5">Причина: {{ person[2] }}</div>
                        </div>
                        <span class="bg-red-600/20 border border-red-500/30 text-red-400 px-2.5 py-1 rounded text-xs font-semibold uppercase">{{ person[3] }} уровень</span>
                    </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    user_data = get_current_user_data()
    return render_template_string(HTML_TEMPLATE, active="home", user_data=user_data)

@app.route("/login-google")
def login_google():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/authorize")
def authorize():
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()
    
    email = user_info.get('email')
    name = user_info.get('name')
    
    session['user'] = email
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (google_email, google_name) VALUES (?, ?)", (email, name))
    conn.commit()
    
    cursor.execute("SELECT registered FROM users WHERE google_email=?", (email,))
    row = cursor.fetchone()
    if row and row[0] == 1:
        session['registered'] = True
    else:
        session.pop('registered', None)
    conn.close()
    
    if row and row[0] == 1:
        return redirect(url_for('index'))
    else:
        return redirect(url_for('register_char'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/register-char", methods=["GET", "POST"])
def register_char():
    if 'user' not in session:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        roblox_nick = request.form.get("roblox_nick")
        ic_name = request.form.get("ic_name")
        age = request.form.get("age")
        job = request.form.get("job")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET roblox_nick=?, ic_name=?, age=?, job=?, registered=1 
            WHERE google_email=?
        """, (roblox_nick, ic_name, age, job, session['user']))
        conn.commit()
        conn.close()
        
        session['registered'] = True
        return redirect(url_for('index'))
        
    user_data = get_current_user_data()
    return render_template_string(HTML_TEMPLATE, active="register", user_data=user_data)

@app.route("/plates")
def plates():
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, plate_number, owner_ic, is_special, price, status FROM plates")
    plates_list = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, active="plates", plates=plates_list)

@app.route("/buy-plate/<int:plate_id>", methods=["POST"])
def buy_plate(plate_id):
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    
    user_data = get_current_user_data()
    ic_name = user_data[4] if user_data else "Гражданин"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE plates SET status='Занят', owner_ic=? WHERE id=?", (ic_name, plate_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('plates'))

@app.route("/fines")
def fines():
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    
    user_data = get_current_user_data()
    ic_name = user_data[4] if user_data else ""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, ic_name, amount, reason, status FROM fines WHERE ic_name=?", (ic_name,))
    fines_list = cursor.fetchall()
    
    if not fines_list:
        cursor.execute("INSERT INTO fines (ic_name, amount, reason, status) VALUES (?, ?, ?, ?)", 
                       (ic_name, 5000, "Превышение скорости на трассе М-1", "Не оплачен"))
        conn.commit()
        cursor.execute("SELECT id, ic_name, amount, reason, status FROM fines WHERE ic_name=?", (ic_name,))
        fines_list = cursor.fetchall()
        
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, active="fines", fines=fines_list)

@app.route("/pay-fine/<int:fine_id>", methods=["POST"])
def pay_fine(fine_id):
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE fines SET status='Оплачен' WHERE id=?", (fine_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('fines'))

@app.route("/wanted")
def wanted():
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, ic_name, reason, level FROM wanted")
    wanted_list = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, active="wanted", wanted=wanted_list)

def get_current_user_data():
    if 'user' not in session:
        return None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, google_email, google_name, roblox_nick, ic_name, age, job, registered FROM users WHERE google_email=?", (session['user'],))
    row = cursor.fetchone()
    if row and row[7] == 1:
        session['registered'] = True
    conn.close()
    return row

if __name__ == "__main__":
    app.run(debug=True)
