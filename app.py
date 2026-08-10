import os
import sqlite3
import requests
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gibdd_rf_secret_key_super_secure")

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_ic TEXT,
            brand TEXT,
            model TEXT,
            plate_number TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ic_name TEXT,
            topic TEXT,
            text TEXT,
            status TEXT DEFAULT 'В рассмотрении'
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

try:
    init_db()
except Exception as e:
    print(f"DB Init Error: {e}")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ФГУП "ГИБДД-РФ" | Портал</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-200 min-h-screen flex flex-col font-sans">
    <!-- Шапка (Строгий официальный стиль) -->
    <header class="bg-gray-950 border-b border-gray-800 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <button id="menu-toggle" class="md:hidden text-gray-300 hover:text-white p-1.5 rounded bg-gray-900 border border-gray-800">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                </button>
                <div class="bg-indigo-900 text-indigo-100 font-bold px-3 py-1 rounded text-sm tracking-wide border border-indigo-700">ГИБДД-РФ</div>
                <span class="text-xs uppercase tracking-wider text-gray-400 font-medium hidden sm:inline">Федеральное государственное унитарное предприятие</span>
            </div>
            <div class="flex items-center space-x-4">
                {% if 'user' in session %}
                    <span class="text-sm text-gray-300 hidden sm:inline">{{ session['user'] }}</span>
                    <a href="/logout" class="bg-gray-800 hover:bg-gray-700 text-gray-200 px-3 py-1.5 rounded text-sm transition border border-gray-700">Выйти</a>
                {% else %}
                    <a href="/login-google" class="bg-indigo-700 hover:bg-indigo-600 text-white px-4 py-1.5 rounded text-sm font-medium transition">Войти через Google</a>
                {% endif %}
            </div>
        </div>
    </header>

    <div id="sidebar-overlay" class="fixed inset-0 bg-black/50 z-30 hidden md:hidden"></div>

    <div class="max-w-7xl mx-auto px-4 py-6 w-full grid grid-cols-1 md:grid-cols-4 gap-6 flex-grow relative">
        
        <!-- Боковое меню (Строгое, без свечений) -->
        <aside id="sidebar" class="fixed md:static inset-y-0 left-0 z-40 w-72 md:w-auto bg-gray-950 border-r md:border border-gray-800 rounded-none md:rounded-lg p-4 h-full md:h-fit transform -translate-x-full md:translate-x-0 transition-transform duration-200 flex flex-col">
            <div class="flex justify-between items-center mb-4 md:hidden px-1">
                <span class="font-bold text-xs text-gray-400 uppercase">Навигация</span>
                <button id="sidebar-close" class="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <h2 class="text-[11px] uppercase tracking-wider text-gray-500 font-bold mb-2 px-2 hidden md:block">Разделы портала</h2>
            <nav class="space-y-1 overflow-y-auto flex-grow text-sm">
                <a href="/" class="block px-3 py-2 rounded transition {% if active == 'home' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">Главная страница</a>
                <a href="/register-char" class="block px-3 py-2 rounded transition {% if active == 'register' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">Профиль персонажа</a>
                
                {% if session.get('registered') %}
                    <div class="pt-3 pb-1 px-2 text-[10px] uppercase font-bold text-gray-600 tracking-wider">Услуги</div>
                    <a href="/plates" class="block px-3 py-2 rounded transition {% if active == 'plates' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">Гос. номера и Блатные</a>
                    <a href="/vehicles" class="block px-3 py-2 rounded transition {% if active == 'vehicles' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">Мой автопарк (ТС)</a>
                    
                    <div class="pt-3 pb-1 px-2 text-[10px] uppercase font-bold text-gray-600 tracking-wider">Контроль и учет</div>
                    <a href="/fines" class="block px-3 py-2 rounded transition {% if active == 'fines' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">База штрафов</a>
                    <a href="/wanted" class="block px-3 py-2 rounded transition {% if active == 'wanted' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">Федеральный розыск</a>
                    <a href="/appeal" class="block px-3 py-2 rounded transition {% if active == 'appeal' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">Подать обращение</a>
                    <a href="/handbook" class="block px-3 py-2 rounded transition {% if active == 'handbook' %}bg-gray-800 text-white font-medium border-l-2 border-indigo-500{% else %}hover:bg-gray-900 text-gray-400 hover:text-gray-200{% endif %}">Справочник КоАП</a>
                {% else %}
                    <div class="pt-4 mt-4 border-t border-gray-800 px-2">
                        <p class="text-xs text-amber-500/90 bg-amber-950/20 p-2.5 rounded border border-amber-900/40 leading-relaxed">
                            Заполните профиль персонажа для разблокировки полного функционала портала.
                        </p>
                    </div>
                {% endif %}
            </nav>
        </aside>

        <!-- Основная область -->
        <main class="md:col-span-3 bg-gray-950 border border-gray-800 rounded-lg p-6">
            {% if error_message %}
                <div class="bg-red-950/30 border border-red-900/50 p-3 rounded mb-4 text-red-400 text-sm">
                    {{ error_message }}
                </div>
            {% endif %}

            {% if active == 'home' %}
                <h1 class="text-xl font-bold mb-3 text-white">Официальный портал ФГУП «ГИБДД-РФ»</h1>
                <p class="text-gray-400 text-sm leading-relaxed mb-6">Государственная инспекция безопасности дорожного движения. Единая информационная система учета транспорта, правонарушений и регламентированных услуг.</p>
                
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6 text-sm">
                    <div class="bg-gray-900 p-4 rounded border border-gray-800">
                        <div class="font-semibold text-gray-200 mb-1">Госреестр</div>
                        <div class="text-xs text-gray-400">Распределение стандартных и номерных знаков категории «Особый учет».</div>
                    </div>
                    <div class="bg-gray-900 p-4 rounded border border-gray-800">
                        <div class="font-semibold text-gray-200 mb-1">Штрафы</div>
                        <div class="text-xs text-gray-400">Автоматическая фиксация и погашение административных взысканий.</div>
                    </div>
                    <div class="bg-gray-900 p-4 rounded border border-gray-800">
                        <div class="font-semibold text-gray-200 mb-1">Розыск</div>
                        <div class="text-xs text-gray-400">База данных транспортных средств и лиц, находящихся в оперативном розыске.</div>
                    </div>
                </div>

                {% if not session.get('user') %}
                    <div class="bg-gray-900 border border-gray-800 p-4 rounded flex items-center justify-between text-sm">
                        <div>
                            <div class="font-medium text-gray-200">Требуется авторизация в системе</div>
                            <div class="text-xs text-gray-400 mt-0.5">Используйте учетную запись Google для продолжения.</div>
                        </div>
                        <a href="/login-google" class="bg-indigo-700 hover:bg-indigo-600 text-white px-4 py-1.5 rounded text-xs font-medium transition">Войти</a>
                    </div>
                {% endif %}

            {% elif active == 'register' %}
                <h1 class="text-xl font-bold mb-2 text-white">Регистрация персонажа</h1>
                <p class="text-xs text-gray-400 mb-6">Укажите достоверные игровые данные для привязки к государственным реестрам.</p>
                
                <form method="POST" action="/register-char" class="space-y-4 max-w-lg text-sm">
                    <div>
                        <label class="block text-xs uppercase text-gray-500 font-semibold mb-1">Ник в Roblox</label>
                        <input type="text" name="roblox_nick" value="{{ user_data[3] if user_data else '' }}" required class="w-full bg-gray-900 border border-gray-800 rounded px-3 py-2 text-gray-200 focus:outline-none focus:border-indigo-600">
                    </div>
                    <div>
                        <label class="block text-xs uppercase text-gray-500 font-semibold mb-1">ФИО IC (Игровое)</label>
                        <input type="text" name="ic_name" value="{{ user_data[4] if user_data else '' }}" required class="w-full bg-gray-900 border border-gray-800 rounded px-3 py-2 text-gray-200 focus:outline-none focus:border-indigo-600">
                    </div>
                    <div>
                        <label class="block text-xs uppercase text-gray-500 font-semibold mb-1">Возраст</label>
                        <input type="number" name="age" value="{{ user_data[5] if user_data else '' }}" required class="w-full bg-gray-900 border border-gray-800 rounded px-3 py-2 text-gray-200 focus:outline-none focus:border-indigo-600">
                    </div>
                    <div>
                        <label class="block text-xs uppercase text-gray-500 font-semibold mb-1">Место работы</label>
                        <input type="text" name="job" value="{{ user_data[6] if user_data else '' }}" required class="w-full bg-gray-900 border border-gray-800 rounded px-3 py-2 text-gray-200 focus:outline-none focus:border-indigo-600">
                    </div>
                    <div class="flex space-x-3 pt-2">
                        <button type="submit" class="bg-indigo-700 hover:bg-indigo-600 text-white px-4 py-2 rounded text-xs font-medium transition">Сохранить данные</button>
                        <a href="/" class="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded text-xs transition flex items-center">Пропустить</a>
                    </div>
                </form>

            {% elif active == 'plates' %}
                <h1 class="text-xl font-bold mb-2 text-white">Распределение государственных знаков</h1>
                <p class="text-xs text-gray-400 mb-6">Приобретение стандартных регистрационных знаков и номеров категории «Особый учет».</p>
                
                <div class="overflow-x-auto text-sm">
                    <table class="w-full text-left text-gray-300">
                        <thead class="bg-gray-900 text-[11px] uppercase text-gray-400 border-b border-gray-800">
                            <tr>
                                <th class="p-3">Номер</th>
                                <th class="p-3">Категория</th>
                                <th class="p-3">Стоимость</th>
                                <th class="p-3">Статус</th>
                                <th class="p-3 text-right">Действие</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-800">
                            {% for plate in plates %}
                            <tr class="hover:bg-gray-900/50">
                                <td class="p-3 font-mono font-bold text-white bg-gray-900/60 rounded border border-gray-800 inline-block my-1">{{ plate[1] }}</td>
                                <td class="p-3 text-xs">{% if plate[3] %}<span class="text-indigo-400 font-medium">Особый учет</span>{% else %}Стандартный{% endif %}</td>
                                <td class="p-3 text-gray-200 font-medium">{{ plate[4] }} ₽</td>
                                <td class="p-3 text-xs"><span class="px-2 py-0.5 rounded {% if plate[5] == 'Занят' %}bg-red-950/40 text-red-400 border border-red-900/50{% else %}bg-green-950/40 text-green-400 border border-green-900/50{% endif %}">{{ plate[5] }}</span></td>
                                <td class="p-3 text-right">
                                    {% if plate[5] == 'Свободен' %}
                                        <form method="POST" action="/buy-plate/{{ plate[0] }}">
                                            <button type="submit" class="bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1 rounded text-xs transition">Получить</button>
                                        </form>
                                    {% else %}
                                        <span class="text-xs text-gray-600">—</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

            {% elif active == 'vehicles' %}
                <h1 class="text-xl font-bold mb-2 text-white">Реестр транспортных средств</h1>
                <p class="text-xs text-gray-400 mb-6">Список транспортных средств, зарегистрированных на ваше имя.</p>
                
                <form method="POST" action="/add-vehicle" class="bg-gray-900 p-4 rounded border border-gray-800 mb-6 space-y-3 max-w-lg text-sm">
                    <div class="font-medium text-gray-200 text-xs uppercase tracking-wider">Регистрация ТС</div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="text" name="brand" placeholder="Марка" required class="bg-gray-950 border border-gray-800 rounded px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-600">
                        <input type="text" name="model" placeholder="Модель" required class="bg-gray-950 border border-gray-800 rounded px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-600">
                    </div>
                    <input type="text" name="plate_number" placeholder="Гос. номер (например: А777АА 77)" required class="w-full bg-gray-950 border border-gray-800 rounded px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-600">
                    <button type="submit" class="bg-indigo-700 hover:bg-indigo-600 text-white px-4 py-1.5 rounded text-xs transition">Зарегистрировать</button>
                </form>

                <div class="space-y-2 text-sm">
                    {% for veh in vehicles %}
                    <div class="bg-gray-900 border border-gray-800 p-3 rounded flex justify-between items-center">
                        <div>
                            <div class="font-medium text-gray-200">{{ veh[2] }} {{ veh[3] }}</div>
                            <div class="text-xs text-gray-400 mt-0.5 font-mono">Гос. знак: {{ veh[4] }}</div>
                        </div>
                    </div>
                    {% else %}
                    <p class="text-xs text-gray-500">Нет зарегистрированных транспортных средств.</p>
                    {% endfor %}
                </div>

            {% elif active == 'fines' %}
                <h1 class="text-xl font-bold mb-2 text-white">База штрафов</h1>
                <p class="text-xs text-gray-400 mb-6">Учет административных правонарушений и задолженностей.</p>
                
                <div class="space-y-2 text-sm">
                    {% for fine in fines %}
                    <div class="bg-gray-900 border border-gray-800 p-3.5 rounded flex justify-between items-center">
                        <div>
                            <div class="font-medium text-gray-200">{{ fine[2] }} ₽ — <span class="text-gray-400">{{ fine[3] }}</span></div>
                            <div class="text-xs text-gray-500 mt-0.5">Статус: <span class="text-amber-400">{{ fine[4] }}</span></div>
                        </div>
                        {% if fine[4] == 'Не оплачен' %}
                        <form method="POST" action="/pay-fine/{{ fine[0] }}">
                            <button type="submit" class="bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 px-3 py-1 rounded text-xs transition">Оплатить</button>
                        </form>
                        {% else %}
                        <span class="text-xs text-green-500">Погашено</span>
                        {% endif %}
                    </div>
                    {% else %}
                    <p class="text-xs text-gray-500">Штрафы и взыскания отсутствуют.</p>
                    {% endfor %}
                </div>

            {% elif active == 'wanted' %}
                <h1 class="text-xl font-bold mb-2 text-white">Федеральный розыск</h1>
                <p class="text-xs text-gray-400 mb-6">Оперативный перечень лиц и объектов транспортного учета.</p>
                
                <div class="space-y-2 text-sm">
                    {% for person in wanted %}
                    <div class="bg-gray-900 border border-gray-800 p-3.5 rounded flex justify-between items-center">
                        <div>
                            <div class="font-medium text-white">{{ person[1] }}</div>
                            <div class="text-xs text-gray-400 mt-0.5">Основание: {{ person[2] }}</div>
                        </div>
                        <span class="bg-red-950/40 border border-red-900/50 text-red-400 px-2 py-0.5 rounded text-[11px] font-medium uppercase">{{ person[3] }} уровень</span>
                    </div>
                    {% endfor %}
                </div>

            {% elif active == 'appeal' %}
                <h1 class="text-xl font-bold mb-2 text-white">Электронная приемная</h1>
                <p class="text-xs text-gray-400 mb-6">Подача официальных обращений и жалоб в адрес руководства ГИБДД.</p>
                
                <form method="POST" action="/send-appeal" class="space-y-3 max-w-lg mb-6 text-sm">
                    <div>
                        <label class="block text-xs uppercase text-gray-500 font-semibold mb-1">Тема</label>
                        <input type="text" name="topic" required placeholder="Тема обращения" class="w-full bg-gray-900 border border-gray-800 rounded px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-600">
                    </div>
                    <div>
                        <label class="block text-xs uppercase text-gray-500 font-semibold mb-1">Текст обращения</label>
                        <textarea name="text" rows="3" required placeholder="Описание сути вопроса..." class="w-full bg-gray-900 border border-gray-800 rounded px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-600"></textarea>
                    </div>
                    <button type="submit" class="bg-indigo-700 hover:bg-indigo-600 text-white px-4 py-1.5 rounded text-xs transition">Направить обращение</button>
                </form>

                <h2 class="text-sm font-bold mb-2 text-gray-300 uppercase tracking-wider">История обращений</h2>
                <div class="space-y-2 text-sm">
                    {% for app_item in appeals %}
                    <div class="bg-gray-900 border border-gray-800 p-3 rounded">
                        <div class="flex justify-between items-start mb-1">
                            <div class="font-medium text-gray-200 text-xs">{{ app_item[2] }}</div>
                            <span class="text-[10px] text-gray-400 bg-gray-950 px-2 py-0.5 rounded border border-gray-800">{{ app_item[4] }}</span>
                        </div>
                        <p class="text-xs text-gray-400">{{ app_item[3] }}</p>
                    </div>
                    {% else %}
                    <p class="text-xs text-gray-500">Обращения не подавались.</p>
                    {% endfor %}
                </div>

            {% elif active == 'handbook' %}
                <h1 class="text-xl font-bold mb-2 text-white">Справочник КоАП РФ</h1>
                <p class="text-xs text-gray-400 mb-6">Выдержки из кодекса административных правонарушений в сфере дорожного движения.</p>
                
                <div class="space-y-2 text-sm">
                    <div class="bg-gray-900 p-3.5 rounded border border-gray-800 flex justify-between items-center">
                        <div>
                            <span class="font-medium text-white">Статья 12.9 ч.2</span> — Превышение скорости (20-40 км/ч)
                        </div>
                        <span class="text-gray-300 font-medium">500 ₽</span>
                    </div>
                    <div class="bg-gray-900 p-3.5 rounded border border-gray-800 flex justify-between items-center">
                        <div>
                            <span class="font-medium text-white">Статья 12.15 ч.4</span> — Выезд на полосу встречного движения
                        </div>
                        <span class="text-gray-300 font-medium">5 000 ₽</span>
                    </div>
                    <div class="bg-gray-900 p-3.5 rounded border border-gray-800 flex justify-between items-center">
                        <div>
                            <span class="font-medium text-white">Статья 12.8 ч.1</span> — Управление в состоянии опьянения
                        </div>
                        <span class="text-gray-300 font-medium">30 000 ₽ + Лишение</span>
                    </div>
                </div>
            {% endif %}
        </main>
    </div>

    <script>
        const menuToggle = document.getElementById('menu-toggle');
        const sidebarClose = document.getElementById('sidebar-close');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        function toggleSidebar() {
            sidebar.classList.toggle('-translate-x-full');
            overlay.classList.toggle('hidden');
        }

        if(menuToggle) menuToggle.addEventListener('click', toggleSidebar);
        if(sidebarClose) sidebarClose.addEventListener('click', toggleSidebar);
        if(overlay) overlay.addEventListener('click', toggleSidebar);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    user_data = get_current_user_data()
    return render_template_string(HTML_TEMPLATE, active="home", user_data=user_data)

@app.route("/login-google")
def login_google():
    if not GOOGLE_CLIENT_ID:
        return render_template_string(HTML_TEMPLATE, active="home", user_data=None, error_message="Ошибка: Не задан GOOGLE_CLIENT_ID.")
    redirect_uri = url_for('authorize', _external=True)
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=openid%20email%20profile"
    return redirect(google_auth_url)

@app.route("/authorize")
def authorize():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    redirect_uri = url_for('authorize', _external=True)
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    token_res = requests.post(token_url, data=data)
    if token_res.status_code != 200:
        return redirect(url_for('index'))
    
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    
    user_res = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {access_token}"})
    if user_res.status_code != 200:
        return redirect(url_for('index'))
        
    user_info = user_res.json()
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

@app.route("/vehicles", methods=["GET", "POST"])
def vehicles():
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    
    user_data = get_current_user_data()
    ic_name = user_data[4] if user_data else ""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == "POST":
        brand = request.form.get("brand")
        model = request.form.get("model")
        plate_number = request.form.get("plate_number")
        cursor.execute("INSERT INTO vehicles (owner_ic, brand, model, plate_number) VALUES (?, ?, ?, ?)", (ic_name, brand, model, plate_number))
        conn.commit()
    
    cursor.execute("SELECT id, owner_ic, brand, model, plate_number FROM vehicles WHERE owner_ic=?", (ic_name,))
    vehicles_list = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, active="vehicles", vehicles=vehicles_list)

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

@app.route("/appeal", methods=["GET", "POST"])
def appeal():
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    
    user_data = get_current_user_data()
    ic_name = user_data[4] if user_data else ""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == "POST":
        topic = request.form.get("topic")
        text = request.form.get("text")
        cursor.execute("INSERT INTO appeals (ic_name, topic, text, status) VALUES (?, ?, ?, ?)", (ic_name, topic, text, 'В рассмотрении'))
        conn.commit()
        
    cursor.execute("SELECT id, ic_name, topic, text, status FROM appeals WHERE ic_name=?", (ic_name,))
    appeals_list = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, active="appeal", appeals=appeals_list)

@app.route("/handbook")
def handbook():
    if not session.get('registered'):
        return redirect(url_for('register_char'))
    return render_template_string(HTML_TEMPLATE, active="handbook")

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
