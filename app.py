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
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans flex flex-col">
    <!-- Шапка -->
    <header class="bg-slate-900 border-b border-slate-800 shadow-lg sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <!-- Кнопка вызова мобильного меню -->
                <button id="menu-toggle" class="md:hidden text-slate-300 hover:text-white p-1.5 rounded-lg bg-slate-800 border border-slate-700 transition">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
                    </svg>
                </button>
                <div class="bg-blue-600 text-white font-black px-3 py-1.5 rounded-lg tracking-wider text-lg shadow-md border border-blue-400">ГИБДД-РФ</div>
                <span class="text-xs uppercase tracking-widest text-slate-400 font-semibold hidden sm:inline">Федеральное государственное унитарное предприятие</span>
            </div>
            <div class="flex items-center space-x-4">
                {% if 'user' in session %}
                    <span class="text-sm text-slate-300 hidden sm:inline">👤 {{ session['user'] }}</span>
                    <a href="/logout" class="bg-red-600 hover:bg-red-700 px-3 py-1.5 rounded text-sm transition font-medium">Выйти</a>
                {% else %}
                    <a href="/login-google" class="bg-white text-slate-900 hover:bg-slate-200 px-4 py-2 rounded font-medium text-sm flex items-center space-x-2 transition shadow">
                        <span>Войти через Google</span>
                    </a>
                {% endif %}
            </div>
        </div>
    </header>

    <!-- Затемнение фона для мобильного меню -->
    <div id="sidebar-overlay" class="fixed inset-0 bg-black/60 z-30 hidden md:hidden backdrop-blur-sm transition-opacity"></div>

    <div class="max-w-7xl mx-auto px-4 py-8 w-full grid grid-cols-1 md:grid-cols-4 gap-6 flex-grow relative">
        
        <!-- Выдвижное боковое меню -->
        <aside id="sidebar" class="fixed md:static inset-y-0 left-0 z-40 w-72 md:w-auto bg-slate-900 border-r md:border border-slate-800 rounded-none md:rounded-xl p-4 shadow-2xl md:shadow-xl h-full md:h-fit transform -translate-x-full md:translate-x-0 transition-transform duration-300 ease-in-out flex flex-col">
            <div class="flex justify-between items-center mb-4 md:hidden px-2">
                <span class="font-bold text-sm text-slate-400 uppercase">Навигация</span>
                <button id="sidebar-close" class="text-slate-400 hover:text-white p-1">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            
            <h2 class="text-xs uppercase tracking-wider text-slate-400 font-bold mb-3 px-2 hidden md:block">Меню управления</h2>
            <nav class="space-y-1.5 overflow-y-auto flex-grow">
                <a href="/" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'home' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">🏠 Главная страница</a>
                <a href="/register-char" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'register' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">👤 Профиль персонажа</a>
                
                {% if session.get('registered') %}
                    <div class="pt-2 pb-1 px-2 text-[10px] uppercase font-bold text-slate-500 tracking-wider">Услуги и реестры</div>
                    <a href="/plates" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'plates' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">🚗 Гос. номера и Блатные</a>
                    <a href="/vehicles" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'vehicles' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">🚙 Мой автопарк (ТС)</a>
                    
                    <div class="pt-2 pb-1 px-2 text-[10px] uppercase font-bold text-slate-500 tracking-wider">Безопасность и закон</div>
                    <a href="/fines" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'fines' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">📜 База штрафов</a>
                    <a href="/wanted" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'wanted' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">🚨 Федеральный розыск</a>
                    <a href="/appeal" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'appeal' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">📝 Подать обращение</a>
                    <a href="/handbook" class="block px-3 py-2.5 rounded-lg text-sm transition {% if active == 'handbook' %}bg-blue-600 text-white font-medium shadow-md shadow-blue-900/50{% else %}hover:bg-slate-800 text-slate-300{% endif %}">📖 Справочник КоАП</a>
                {% else %}
                    <div class="pt-4 mt-4 border-t border-slate-800 px-2">
                        <p class="text-xs text-amber-400 bg-amber-950/40 p-3 rounded-lg border border-amber-800/50 leading-relaxed">
                            ⚠️ 90% функций заблокировано. Заполните профиль персонажа, чтобы разблокировать доступ.
                        </p>
                    </div>
                {% endif %}
            </nav>
        </aside>

        <!-- Основной контент -->
        <main class="md:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            {% if error_message %}
                <div class="bg-red-950/40 border border-red-900 p-4 rounded-lg mb-6 text-red-400 text-sm">
                    {{ error_message }}
                </div>
            {% endif %}

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
                <p class="text-xs text-slate-400 mb-6">Получите стандартный номер или приобретите уникальный «блаттнный» госзнак.</p>
                
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

            {% elif active == 'vehicles' %}
                <h1 class="text-2xl font-bold mb-4">Мой автопарк</h1>
                <p class="text-xs text-slate-400 mb-6">Зарегистрированные за вами транспортные средства.</p>
                
                <form method="POST" action="/add-vehicle" class="bg-slate-950 p-4 rounded-lg border border-slate-800 mb-6 space-y-3 max-w-lg">
                    <h3 class="text-sm font-semibold text-white">Добавить транспортное средство</h3>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="text" name="brand" placeholder="Марка (например: BMW)" required class="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                        <input type="text" name="model" placeholder="Модель (например: M5 F90)" required class="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <input type="text" name="plate_number" placeholder="Гос. номер (например: А777АА 77)" required class="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-xs font-medium transition">Зарегистрировать авто</button>
                </form>

                <div class="space-y-3">
                    {% for veh in vehicles %}
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-lg flex justify-between items-center">
                        <div>
                            <div class="text-sm font-bold text-white">{{ veh[2] }} {{ veh[3] }}</div>
                            <div class="text-xs text-slate-400 mt-0.5">Гос. номер: <span class="font-mono text-blue-400 font-semibold">{{ veh[4] }}</span></div>
                        </div>
                    </div>
                    {% else %}
                    <p class="text-sm text-slate-400">У вас нет зарегистрированных автомобилей.</p>
                    {% endfor %}
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

            {% elif active == 'appeal' %}
                <h1 class="text-2xl font-bold mb-4">Подача обращения / Жалобы</h1>
                <p class="text-xs text-slate-400 mb-6">Свяжитесь с руководством ФГУП «ГИБДД-РФ» по вопросам работы сотрудников или обжалования штрафов.</p>
                
                <form method="POST" action="/send-appeal" class="space-y-4 max-w-lg mb-8">
                    <div>
                        <label class="block text-xs uppercase font-semibold text-slate-400 mb-1">Тема обращения</label>
                        <input type="text" name="topic" required placeholder="Например: Обжалование штрафа №4" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <div>
                        <label class="block text-xs uppercase font-semibold text-slate-400 mb-1">Суть обращения / Описание</label>
                        <textarea name="text" rows="4" required placeholder="Опишите ситуацию подробно..." class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"></textarea>
                    </div>
                    <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition shadow">Отправить жалобу</button>
                </form>

                <h2 class="text-lg font-bold mb-3">Ваши обращения</h2>
                <div class="space-y-3">
                    {% for app_item in appeals %}
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                        <div class="flex justify-between items-start">
                            <div class="text-sm font-bold text-white">{{ app_item[2] }}</div>
                            <span class="px-2 py-0.5 rounded text-xs bg-blue-950 text-blue-400 border border-blue-900">{{ app_item[4] }}</span>
                        </div>
                        <p class="text-xs text-slate-300 mt-2">{{ app_item[3] }}</p>
                    </div>
                    {% else %}
                    <p class="text-sm text-slate-400">Вы пока не отправляли обращений.</p>
                    {% endfor %}
                </div>

            {% elif active == 'handbook' %}
                <h1 class="text-2xl font-bold mb-4">Справочник КоАП и штрафов</h1>
                <p class="text-xs text-slate-400 mb-6">Основные статьи и размеры взысканий за административные правонарушения на дороге.</p>
                
                <div class="space-y-3 text-sm">
                    <div class="bg-slate-950 p-4 rounded-lg border border-slate-800 flex justify-between items-center">
                        <div>
                            <span class="font-bold text-white">Статья 12.9 ч.2</span> — Превышение скорости (на 20-40 км/ч)
                        </div>
                        <span class="text-emerald-400 font-semibold">500 ₽</span>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-lg border border-slate-800 flex justify-between items-center">
                        <div>
                            <span class="font-bold text-white">Статья 12.15 ч.4</span> — Выезд на встречную полосу
                        </div>
                        <span class="text-emerald-400 font-semibold">5 000 ₽</span>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-lg border border-slate-800 flex justify-between items-center">
                        <div>
                            <span class="font-bold text-white">Статья 12.8 ч.1</span> — Управление ТС в состоянии опьянения
                        </div>
                        <span class="text-emerald-400 font-semibold">30 000 ₽ + Лишение</span>
                    </div>
                </div>
            {% endif %}
        </main>
    </div>

    <!-- Скрипт для работы выдвижного меню на мобильных -->
    <script>
        const menuToggle = document.getElementById('menu-toggle');
        const sidebarClose = document.getElementById('sidebar-close');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        function toggleSidebar() {
            sidebar.classList.toggle('-translate-x-full');
            overlay.classList.toggle('hidden');
        }

        menuToggle.addEventListener('click', toggleSidebar);
        sidebarClose.addEventListener('click', toggleSidebar);
        overlay.addEventListener('click', toggleSidebar);
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
        return render_template_string(HTML_TEMPLATE, active="home", user_data=None, error_message="Ошибка: Не задан GOOGLE_CLIENT_ID в переменных окружения Vercel.")
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
