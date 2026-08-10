import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
DB_NAME = "database.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT UNIQUE,
            user_id INTEGER REFERENCES users(id),
            price INTEGER,
            rarity INTEGER
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            code TEXT,
            date TEXT,
            reason TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS wanted (
            plate TEXT PRIMARY KEY,
            reason TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT,
            type TEXT,
            desc TEXT,
            date TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS auction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT,
            price INTEGER,
            author TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            date TEXT
        )''')
        conn.commit()

init_db()

def add_log(msg):
    with get_db() as conn:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO logs (message, date) VALUES (?, ?)", (msg, timestamp))
        conn.commit()

def calculate_plate_details(plate):
    rarity = (sum(ord(c) for c in plate) % 90) + 10
    price = rarity * 25000
    return rarity, price

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ФГУП «ГИБДД-РФ» — База данных</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background-color: #0d1117; color: #c9d1d9; display: flex; min-height: 100vh; }
        
        sidebar { width: 260px; background-color: #161b22; border-right: 1px solid #30363d; display: flex; flex-direction: column; padding: 20px; position: fixed; height: 100vh; }
        .brand { font-size: 16px; font-weight: bold; color: #ffd700; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 1px; }
        .nav-link { display: block; padding: 12px 15px; color: #c9d1d9; text-decoration: none; border-radius: 6px; margin-bottom: 5px; font-size: 14px; transition: 0.2s; cursor: pointer; }
        .nav-link:hover, .nav-link.active { background-color: #30363d; color: #ffd700; }

        .main { margin-left: 260px; flex: 1; padding: 30px; overflow-y: auto; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        h2 { color: #ffd700; margin-bottom: 20px; font-size: 22px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; text-align: center; }
        .stat-card h3 { font-size: 28px; color: #ffd700; margin-bottom: 5px; }
        .stat-card p { font-size: 12px; color: #8b949e; text-transform: uppercase; }

        table { width: 100%; border-collapse: collapse; background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; margin-top: 15px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #30363d; font-size: 14px; }
        th { background: #21262d; color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 11px; }
        tr:hover { background: rgba(255,255,255,0.02); }

        .plate-num { font-family: monospace; font-weight: bold; color: #ffd700; font-size: 15px; }
        .price-val { color: #7ee787; font-weight: 600; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; display: inline-block; }
        .badge-normal { background: rgba(126,231,135,0.15); color: #7ee787; }
        .badge-wanted { background: rgba(218,54,51,0.15); color: #da3633; }
        .badge-fine { background: rgba(218,54,51,0.2); color: #f85149; font-family: monospace; }

        .btn { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: 0.2s; display: inline-flex; align-items: center; gap: 5px; text-decoration: none; }
        .btn:hover { background: #30363d; border-color: #8b949e; }
        .btn-primary { background: #1f6feb; color: white; border-color: transparent; }
        .btn-primary:hover { background: #388bfd; }
        .btn-danger { background: #da3633; color: white; border-color: transparent; }
        .btn-danger:hover { background: #f85149; }
        .btn-success { background: #238636; color: white; border-color: transparent; }
        .btn-success:hover { background: #2ea043; }

        .form-control { background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 8px 12px; border-radius: 6px; font-size: 14px; width: 100%; margin-bottom: 10px; }
        .form-control:focus { outline: none; border-color: #1f6feb; }
        
        .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; gap: 10px; }

        #toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 1000; display: flex; flex-direction: column; gap: 10px; }
        .toast { padding: 12px 20px; border-radius: 6px; font-size: 13px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.5); opacity: 0; transition: opacity 0.3s ease; }
        .toast.show { opacity: 1; }
        .toast-success { background: #238636; }
        .toast-error { background: #da3633; }

        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 500; justify-content: center; align-items: center; }
        .modal.active { display: flex; }
        .modal-box { background: #161b22; border: 1px solid #30363d; border-radius: 8px; width: 400px; padding: 25px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .modal-header { font-size: 16px; font-weight: bold; color: #ffd700; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        .modal-close { background: none; border: none; color: #8b949e; font-size: 18px; cursor: pointer; }

        .logs-box { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 15px; font-family: monospace; font-size: 12px; height: 250px; overflow-y: auto; color: #8b949e; line-height: 1.5; }

        @media(max-width: 768px) {
            sidebar { width: 70px; padding: 10px; }
            sidebar .brand, sidebar .nav-link span { display: none; }
            .main { margin-left: 70px; padding: 15px; }
            .stats-grid { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>

    <sidebar>
        <div class="brand">🚗 ГИБДД РФ</div>
        <div class="nav-link active" onclick="switchTab('dashboard', this)">📊 <span>Дашборд</span></div>
        <div class="nav-link" onclick="switchTab('plates', this)">🚙 <span>Номера</span></div>
        <div class="nav-link" onclick="switchTab('users', this)">👥 <span>Пользователи</span></div>
        <div class="nav-link" onclick="switchTab('fines', this)">⚠️ <span>Штрафы</span></div>
        <div class="nav-link" onclick="switchTab('auction', this)">📈 <span>Аукцион</span></div>
        <div class="nav-link" onclick="switchTab('dossier', this)">📋 <span>Досье</span></div>
    </sidebar>

    <div class="main">
        <div id="dashboard" class="tab-content active">
            <h2>Дашборд оперативного управления</h2>
            <div class="stats-grid">
                <div class="stat-card"><h3 id="stat-plates">0</h3><p>Всего номеров</p></div>
                <div class="stat-card"><h3 id="stat-users">0</h3><p>Пользователей</p></div>
                <div class="stat-card"><h3 id="stat-fines">0</h3><p>Штрафов</p></div>
                <div class="stat-card"><h3 id="stat-wanted">0</h3><p>В розыске</p></div>
            </div>
            <h3 style="color: #c9d1d9; font-size: 16px; margin-bottom: 10px;">Лента последних действий</h3>
            <div class="logs-box" id="logs-container">Загрузка логов...</div>
        </div>

        <div id="plates" class="tab-content">
            <h2>Управление номерами</h2>
            <div class="toolbar">
                <input type="text" id="plate-search" class="form-control" placeholder="Поиск по номеру или владельцу..." style="max-width: 300px; margin-bottom: 0;" oninput="filterPlates()">
                <div>
                    <button class="btn btn-primary" onclick="openModal('modal-give')">➕ Выдать номер</button>
                    <button class="btn" onclick="loadPlates()">🔄 Обновить</button>
                </div>
            </div>
            <table>
                <thead>
                    <tr><th>Номер</th><th>Владелец</th><th>Цена</th><th>Редкость</th><th>Статус</th><th>Действия</th></tr>
                </thead>
                <tbody id="plates-table-body">
                    <tr><td colspan="6" style="text-align: center;">Загрузка...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="users" class="tab-content">
            <h2>Реестр пользователей</h2>
            <table>
                <thead>
                    <tr><th>Пользователь / ID</th><th>Количество номеров</th><th>Количество штрафов</th><th>Общая стоимость</th></tr>
                </thead>
                <tbody id="users-table-body">
                    <tr><td colspan="4" style="text-align: center;">Загрузка...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="fines" class="tab-content">
            <h2>База штрафов и нарушений</h2>
            <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h3 style="font-size: 15px; color: #ffd700; margin-bottom: 12px;">➕ Выписать новый штраф</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr 2fr auto; gap: 10px;">
                    <input type="text" id="fine-code" class="form-control" placeholder="Статья (например, 264.1)" style="margin-bottom:0;">
                    <input type="text" id="fine-user" class="form-control" placeholder="Пользователь (ID или Имя)" style="margin-bottom:0;">
                    <input type="text" id="fine-reason" class="form-control" placeholder="Причина нарушения" style="margin-bottom:0;">
                    <button class="btn btn-primary" onclick="addFine()">Добавить</button>
                </div>
            </div>
            <table>
                <thead>
                    <tr><th>Статья</th><th>Пользователь</th><th>Дата</th><th>Причина</th><th>Действия</th></tr>
                </thead>
                <tbody id="fines-table-body">
                    <tr><td colspan="5" style="text-align: center;">Загрузка...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="auction" class="tab-content">
            <h2>Аукцион госномеров</h2>
            <div id="auction-container" style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 30px; text-align: center; max-width: 500px; margin: 40px auto;">
                Загрузка аукциона...
            </div>
        </div>

        <div id="dossier" class="tab-content">
            <h2>Досье транспортного средства</h2>
            <div class="toolbar" style="max-width: 500px;">
                <input type="text" id="dossier-input" class="form-control" placeholder="Введите госномер..." style="margin-bottom: 0;" oninput="this.value = this.value.toUpperCase()">
                <button class="btn btn-primary" onclick="loadDossier()">🔍 Найти</button>
            </div>
            <div id="dossier-result" style="margin-top: 20px;">
                <p style="color: #8b949e;">Введите номер выше для получения полной оперативной сводки.</p>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <div id="modal-give" class="modal">
        <div class="modal-box">
            <div class="modal-header"><span>🎖️ Выдать номер</span><button class="modal-close" onclick="closeModal('modal-give')">&times;</button></div>
            <label style="font-size: 12px; color: #8b949e;">Пользователь</label>
            <select id="give-user-select" class="form-control"></select>
            <label style="font-size: 12px; color: #8b949e;">Госномер</label>
            <input type="text" id="give-plate-input" class="form-control" placeholder="А777МР777" oninput="this.value = this.value.toUpperCase()">
            <button class="btn btn-success" style="width: 100%; justify-content: center; margin-top: 10px;" onclick="submitGivePlate()">✅ Выдать</button>
        </div>
    </div>

    <div id="modal-protocol" class="modal">
        <div class="modal-box">
            <div class="modal-header"><span>📋 Составить протокол</span><button class="modal-close" onclick="closeModal('modal-protocol')">&times;</button></div>
            <label style="font-size: 12px; color: #8b949e;">Госномер</label>
            <input type="text" id="proto-plate" class="form-control" readonly>
            <label style="font-size: 12px; color: #8b949e;">Тип нарушения</label>
            <select id="proto-type" class="form-control">
                <option value="Нарушение ПДД">Нарушение ПДД</option>
                <option value="Незаконная продажа">Незаконная продажа</option>
                <option value="Подделка">Подделка</option>
                <option value="Розыск">Розыск</option>
            </select>
            <label style="font-size: 12px; color: #8b949e;">Описание</label>
            <textarea id="proto-desc" class="form-control" placeholder="Детали нарушения..." rows="3"></textarea>
            <button class="btn btn-primary" style="width: 100%; justify-content: center; margin-top: 10px;" onclick="submitProtocol()">Составить</button>
        </div>
    </div>

    <div id="modal-wanted" class="modal">
        <div class="modal-box">
            <div class="modal-header"><span>🚨 Объявить в розыск</span><button class="modal-close" onclick="closeModal('modal-wanted')">&times;</button></div>
            <label style="font-size: 12px; color: #8b949e;">Госномер</label>
            <input type="text" id="wanted-plate" class="form-control" readonly>
            <label style="font-size: 12px; color: #8b949e;">Причина розыска</label>
            <input type="text" id="wanted-reason" class="form-control" placeholder="Угон, ДТП со скрытием...">
            <button class="btn btn-danger" style="width: 100%; justify-content: center; margin-top: 10px;" onclick="submitWanted()">🚨 Объявить в розыск</button>
        </div>
    </div>

    <div id="toast-container"></div>

    <script>
        let allPlatesCache = [];

        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast toast-${type} show`;
            toast.innerText = message;
            container.appendChild(toast);
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        function switchTab(tabId, el) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            if(el) el.classList.add('active');
            
            if(tabId === 'dashboard') loadDashboard();
            if(tabId === 'plates') loadPlates();
            if(tabId === 'users') loadUsers();
            if(tabId === 'fines') loadFines();
            if(tabId === 'auction') loadAuction();
        }

        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        function loadDashboard() {
            fetch('/api/stats').then(res => res.json()).then(data => {
                document.getElementById('stat-plates').innerText = data.total_plates;
                document.getElementById('stat-users').innerText = data.total_users;
                document.getElementById('stat-fines').innerText = data.total_fines;
                document.getElementById('stat-wanted').innerText = data.total_wanted;
            });
            fetch('/api/logs').then(res => res.json()).then(logs => {
                document.getElementById('logs-container').innerHTML = logs.length > 0 ? logs.join('<br>') : 'Логи отсутствуют';
            });
        }

        function loadPlates() {
            fetch('/api/plates').then(res => res.json()).then(data => {
                allPlatesCache = data;
                renderPlatesTable(data);
                fetch('/api/users').then(r => r.json()).then(users => {
                    const sel = document.getElementById('give-user-select');
                    sel.innerHTML = users.map(u => `<option value="${u.id}">${u.name} (ID: ${u.id})</option>`).join('');
                });
            });
        }

        function renderPlatesTable(data) {
            const tbody = document.getElementById('plates-table-body');
            if(data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Нет зарегистрированных номеров</td></tr>';
                return;
            }
            tbody.innerHTML = data.map(p => `
                <tr>
                    <td class="plate-num">${p.plate}</td>
                    <td>${p.owner}</td>
                    <td class="price-val">${p.price.toLocaleString()} ₽</td>
                    <td>⭐ ${p.rarity}/100</td>
                    <td><span class="badge ${p.wanted ? 'badge-wanted' : 'badge-normal'}">${p.wanted ? '🚨 Розыск' : '✅ В норме'}</span></td>
                    <td>
                        <button class="btn" title="Досье" onclick="openDossier('${p.plate}')">📋</button>
                        <button class="btn btn-danger" title="Забрать" onclick="revokePlate('${p.plate}')">⛔</button>
                        <button class="btn" title="Протокол" onclick="openProtocolModal('${p.plate}')">📋</button>
                        ${p.wanted ? 
                            `<button class="btn btn-success" title="Снять с розыска" onclick="unwantedPlate('${p.plate}')">✅</button>` :
                            `<button class="btn btn-danger" title="Объявить в розыск" onclick="openWantedModal('${p.plate}')">🚨</button>`
                        }
                    </td>
                </tr>
            `).join('');
        }

        function filterPlates() {
            const query = document.getElementById('plate-search').value.toLowerCase();
            const filtered = allPlatesCache.filter(p => p.plate.toLowerCase().includes(query) || p.owner.toLowerCase().includes(query));
            renderPlatesTable(filtered);
        }

        function loadUsers() {
            fetch('/api/users').then(res => res.json()).then(data => {
                const tbody = document.getElementById('users-table-body');
                if(data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">Нет пользователей</td></tr>';
                    return;
                }
                tbody.innerHTML = data.map(u => `
                    <tr>
                        <td><b>ID ${u.id}</b> (${u.name})</td>
                        <td>${u.plates_count}</td>
                        <td>${u.fines_count}</td>
                        <td class="price-val">${u.total_value.toLocaleString()} ₽</td>
                    </tr>
                `).join('');
            });
        }

        function loadFines() {
            fetch('/api/fines').then(res => res.json()).then(data => {
                const tbody = document.getElementById('fines-table-body');
                if(data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Штрафов нет</td></tr>';
                    return;
                }
                tbody.innerHTML = data.map(f => `
                    <tr>
                        <td><span class="badge badge-fine">${f.code}</span></td>
                        <td>${f.user}</td>
                        <td>${f.date.replace('T', ' ')}</td>
                        <td>${f.reason}</td>
                        <td><button class="btn btn-success" onclick="removeFine('${f.code}', ${f.user_id})">✅ Снять</button></td>
                    </tr>
                `).join('');
            });
        }

        function addFine() {
            const code = document.getElementById('fine-code').value.trim();
            const user = document.getElementById('fine-user').value.trim();
            const reason = document.getElementById('fine-reason').value.trim();
            if(!code || !user || !reason) {
                showToast('Заполните все поля штрафа', 'error');
                return;
            }
            fetch('/api/fine/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code, user, reason})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Штраф успешно добавлен');
                    document.getElementById('fine-code').value = '';
                    document.getElementById('fine-user').value = '';
                    document.getElementById('fine-reason').value = '';
                    loadFines();
                } else {
                    showToast(resp.error || 'Ошибка', 'error');
                }
            });
        }

        function removeFine(code, userId) {
            if(!confirm('Снять данный штраф?')) return;
            fetch('/api/fine/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code, user_id: userId})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Штраф снят');
                    loadFines();
                } else {
                    showToast('Ошибка', 'error');
                }
            });
        }

        function loadAuction() {
            fetch('/api/auction').then(res => res.json()).then(data => {
                const container = document.getElementById('auction-container');
                if(!data.plate) {
                    container.innerHTML = '<p style="color: #8b949e;">❌ На аукционе нет лотов</p>';
                    return;
                }
                container.innerHTML = `
                    <p style="font-size: 12px; color: #8b949e; text-transform: uppercase; margin-bottom: 5px;">Текущий лот</p>
                    <div class="plate-num" style="font-size: 32px; margin-bottom: 15px;">${data.plate}</div>
                    <p style="font-size: 14px; color: #c9d1d9; margin-bottom: 5px;">Продавец: <b>${data.author}</b></p>
                    <p style="font-size: 18px; margin-bottom: 20px;">Ставка: <span class="price-val">${data.price.toLocaleString()} ₽</span></p>
                    <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                        <input type="number" id="bid-amount" class="form-control" placeholder="Сумма ставки..." style="margin-bottom:0;">
                        <button class="btn btn-primary" onclick="placeBid()">📈 Ставка</button>
                    </div>
                    <button class="btn btn-danger" style="width: 100%; justify-content: center;" onclick="endAuction()">⛔ Завершить аукцион</button>
                `;
            });
        }

        function placeBid() {
            const amount = parseInt(document.getElementById('bid-amount').value);
            if(!amount) {
                showToast('Введите корректную сумму', 'error');
                return;
            }
            fetch('/api/bid', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({amount})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Ставка принята!');
                    loadAuction();
                } else {
                    showToast(resp.error || 'Ставка слишком мала', 'error');
                }
            });
        }

        function endAuction() {
            if(!confirm('Завершить аукцион?')) return;
            fetch('/api/auction/end', {method: 'POST'}).then(() => {
                showToast('Аукцион завершен');
                loadAuction();
            });
        }

        function openDossier(plate) {
            switchTab('dossier', document.querySelectorAll('.nav-link')[5]);
            document.getElementById('dossier-input').value = plate;
            loadDossier();
        }

        function loadDossier() {
            const plate = document.getElementById('dossier-input').value.trim();
            if(!plate) return;
            fetch(`/api/dossier/${encodeURIComponent(plate)}`).then(res => res.json()).then(data => {
                const resDiv = document.getElementById('dossier-result');
                if(!data.found) {
                    resDiv.innerHTML = `<p style="color: #da3633;">Транспортное средство с номером ${plate} не найдено в базе.</p>`;
                    return;
                }
                resDiv.innerHTML = `
                    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <span class="plate-num" style="font-size: 24px;">${data.plate}</span>
                            <span class="badge ${data.wanted ? 'badge-wanted' : 'badge-normal'}">${data.wanted ? '🚨 РОЗЫСК: ' + data.wanted_reason : '✅ В норме'}</span>
                        </div>
                        <p style="margin-bottom: 8px;"><b>Владелец:</b> ${data.owner}</p>
                        <p style="margin-bottom: 8px;"><b>Оценочная стоимость:</b> <span class="price-val">${data.price.toLocaleString()} ₽</span></p>
                        <p style="margin-bottom: 15px;"><b>Редкость:</b> ⭐ ${data.rarity}/100</p>
                        <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                            <button class="btn" onclick="openProtocolModal('${data.plate}')">📋 Протокол</button>
                            ${data.wanted ? 
                                `<button class="btn btn-success" onclick="unwantedPlate('${data.plate}'); setTimeout(loadDossier, 300);">✅ Снять розыск</button>` :
                                `<button class="btn btn-danger" onclick="openWantedModal('${data.plate}')">🚨 Розыск</button>`
                            }
                            <button class="btn btn-danger" onclick="revokePlate('${data.plate}'); document.getElementById('dossier-result').innerHTML='';">⛔ Забрать</button>
                        </div>
                        <h3 style="font-size: 15px; color: #ffd700; margin-bottom: 10px;">История протоколов и событий</h3>
                        <table>
                            <thead><tr><th>Дата</th><th>Тип</th><th>Описание</th></tr></thead>
                            <tbody>
                                ${data.history.length === 0 ? '<tr><td colspan="3">История пуста</td></tr>' : 
                                    data.history.map(h => `<tr><td>${h.date}</td><td><b>${h.type}</b></td><td>${h.desc}</td></tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            });
        }

        function submitGivePlate() {
            const user_id = document.getElementById('give-user-select').value;
            const plate = document.getElementById('give-plate-input').value.trim();
            if(!plate) {
                showToast('Введите госномер', 'error');
                return;
            }
            fetch('/api/give', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id, plate})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Номер успешно выдан');
                    closeModal('modal-give');
                    loadPlates();
                } else {
                    showToast(resp.error || 'Номер уже занят', 'error');
                }
            });
        }

        function revokePlate(plate) {
            if(!confirm(`Забрать номер ${plate} у владельца?`)) return;
            fetch('/api/revoke', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({plate})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Номер успешно изъят');
                    loadPlates();
                } else {
                    showToast('Ошибка изъятия', 'error');
                }
            });
        }

        function openProtocolModal(plate) {
            document.getElementById('proto-plate').value = plate;
            document.getElementById('proto-desc').value = '';
            openModal('modal-protocol');
        }

        function submitProtocol() {
            const plate = document.getElementById('proto-plate').value;
            const type = document.getElementById('proto-type').value;
            const desc = document.getElementById('proto-desc').value.trim();
            if(!desc) {
                showToast('Заполните описание', 'error');
                return;
            }
            fetch('/api/protocol', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({plate, type, desc})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Протокол успешно составлен');
                    closeModal('modal-protocol');
                    loadPlates();
                } else {
                    showToast('Ошибка', 'error');
                }
            });
        }

        function openWantedModal(plate) {
            document.getElementById('wanted-plate').value = plate;
            document.getElementById('wanted-reason').value = '';
            openModal('modal-wanted');
        }

        function submitWanted() {
            const plate = document.getElementById('wanted-plate').value;
            const reason = document.getElementById('wanted-reason').value.trim();
            if(!reason) {
                showToast('Укажите причину розыска', 'error');
                return;
            }
            fetch('/api/wanted', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({plate, reason})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Транспорт объявлен в розыск');
                    closeModal('modal-wanted');
                    loadPlates();
                } else {
                    showToast('Ошибка', 'error');
                }
            });
        }

        function unwantedPlate(plate) {
            if(!confirm(`Снять транспорт ${plate} с розыска?`)) return;
            fetch('/api/unwanted', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({plate})
            }).then(res => res.json()).then(resp => {
                if(resp.success) {
                    showToast('Розыск успешно снят');
                    loadPlates();
                } else {
                    showToast('Ошибка', 'error');
                }
            });
        }

        setInterval(() => {
            if(document.getElementById('dashboard').classList.contains('active')) {
                loadDashboard();
            }
        }, 15000);

        loadDashboard();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/stats")
def api_stats():
    with get_db() as conn:
        total_plates = conn.execute("SELECT COUNT(*) FROM plates").fetchone()[0]
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_fines = conn.execute("SELECT COUNT(*) FROM fines").fetchone()[0]
        total_wanted = conn.execute("SELECT COUNT(*) FROM wanted").fetchone()[0]
    return jsonify({
        "total_plates": total_plates,
        "total_users": total_users,
        "total_fines": total_fines,
        "total_wanted": total_wanted
    })

@app.route("/api/plates")
def api_plates():
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT p.plate, u.name as owner, p.price, p.rarity, w.plate as wanted_plate
            FROM plates p
            LEFT JOIN users u ON p.user_id = u.id
            LEFT JOIN wanted w ON p.plate = w.plate
        ''')
        rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "plate": row["plate"],
            "owner": row["owner"] or "Неизвестен",
            "price": row["price"],
            "rarity": row["rarity"],
            "wanted": row["wanted_plate"] is not None
        })
    return jsonify(result)

@app.route("/api/users")
def api_users():
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT u.id, u.name,
                   COUNT(DISTINCT p.id) as plates_count,
                   COUNT(DISTINCT f.id) as fines_count,
                   COALESCE(SUM(p.price), 0) as total_value
            FROM users u
            LEFT JOIN plates p ON u.id = p.user_id
            LEFT JOIN fines f ON u.id = f.user_id
            GROUP BY u.id
            ORDER BY plates_count DESC
        ''')
        rows = cursor.fetchall()
    users_list = []
    for row in rows:
        users_list.append({
            "id": row["id"],
            "name": row["name"],
            "plates_count": row["plates_count"],
            "fines_count": row["fines_count"],
            "total_value": row["total_value"]
        })
    return jsonify(users_list)

@app.route("/api/fines")
def api_fines():
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT f.code, u.name as user_name, u.id as user_id, f.date, f.reason
            FROM fines f
            JOIN users u ON f.user_id = u.id
        ''')
        rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "code": row["code"],
            "user": row["user_name"],
            "user_id": row["user_id"],
            "date": row["date"],
            "reason": row["reason"]
        })
    return jsonify(result)

@app.route("/api/auction")
def api_auction():
    with get_db() as conn:
        row = conn.execute("SELECT plate, price, author FROM auction ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        return jsonify({"plate": row["plate"], "price": row["price"], "author": row["author"]})
    return jsonify({})

@app.route("/api/logs")
def api_logs():
    with get_db() as conn:
        rows = conn.execute("SELECT date, message FROM logs ORDER BY id DESC LIMIT 20").fetchall()
    logs = [f"{row['date']} - {row['message']}" for row in rows]
    return jsonify(logs)

@app.route("/api/dossier/<plate>")
def api_dossier(plate):
    plate = plate.upper().strip()
    with get_db() as conn:
        p_row = conn.execute('''
            SELECT p.plate, u.name as owner, p.price, p.rarity
            FROM plates p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.plate = ?
        ''', (plate,)).fetchone()
        
        w_row = conn.execute("SELECT reason FROM wanted WHERE plate = ?", (plate,)).fetchone()
        h_rows = conn.execute("SELECT type, desc, date FROM history WHERE plate = ? ORDER BY id DESC LIMIT 10", (plate,)).fetchall()
    
    if not p_row and not w_row and not h_rows:
        return jsonify({"found": False})
    
    owner = p_row["owner"] if p_row and p_row["owner"] else ("Неизвестен / В розыске" if w_row else "Неизвестен")
    rarity, price = calculate_plate_details(plate)
    if p_row:
        price = p_row["price"]
        rarity = p_row["rarity"]
        
    is_wanted = w_row is not None
    wanted_reason = w_row["reason"] if w_row else ""
    history = [{"type": h["type"], "desc": h["desc"], "date": h["date"]} for h in h_rows]
    
    return jsonify({
        "found": True,
        "plate": plate,
        "owner": owner,
        "price": price,
        "rarity": rarity,
        "wanted": is_wanted,
        "wanted_reason": wanted_reason,
        "history": history
    })

@app.route("/api/give", methods=["POST"])
def api_give():
    req = request.json or {}
    user_id = req.get("user_id")
    plate = req.get("plate", "").strip().upper()
    if not user_id or not plate:
        return jsonify({"success": False, "error": "Заполните все поля"})
    rarity, price = calculate_plate_details(plate)
    try:
        with get_db() as conn:
            existing = conn.execute("SELECT id FROM plates WHERE plate = ?", (plate,)).fetchone()
            if existing:
                return jsonify({"success": False, "error": "Номер уже занят"})
            conn.execute("INSERT INTO plates (plate, user_id, price, rarity) VALUES (?, ?, ?, ?)", (plate, user_id, price, rarity))
            conn.commit()
        add_log(f"Выдан госномер {plate} пользователю ID {user_id}")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/revoke", methods=["POST"])
def api_revoke():
    req = request.json or {}
    plate = req.get("plate")
    if not plate:
        return jsonify({"success": False, "error": "Не указан номер"})
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM plates WHERE plate = ?", (plate,))
        conn.commit()
        if cursor.rowcount > 0:
            add_log(f"Изъят госномер {plate}")
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Номер не найден"})

@app.route("/api/fine/add", methods=["POST"])
def api_fine_add():
    req = request.json or {}
    code = req.get("code")
    user_input = req.get("user")
    reason = req.get("reason")
    if not code or not user_input or not reason:
        return jsonify({"success": False, "error": "Заполните все поля"})
    
    with get_db() as conn:
        u_row = conn.execute("SELECT id FROM users WHERE id = ? OR name = ?", (user_input, user_input)).fetchone()
        if not u_row:
            conn.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (str(user_input),))
            conn.commit()
            u_row = conn.execute("SELECT id FROM users WHERE name = ?", (str(user_input),)).fetchone()
        user_id = u_row["id"] if u_row else None
        if not user_id:
            return jsonify({"success": False, "error": "Пользователь не найден"})
        
        date_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
        conn.execute("INSERT INTO fines (user_id, code, date, reason) VALUES (?, ?, ?, ?)", (user_id, code, date_str, reason))
        conn.commit()
    add_log(f"Выписан штраф ст. {code} пользователю {user_input}")
    return jsonify({"success": True})

@app.route("/api/fine/remove", methods=["POST"])
def api_fine_remove():
    req = request.json or {}
    code = req.get("code")
    user_id = req.get("user_id")
    with get_db() as conn:
        conn.execute("DELETE FROM fines WHERE code = ? AND user_id = ?", (code, user_id))
        conn.commit()
    add_log(f"Снят штраф ст. {code} у пользователя ID {user_id}")
    return jsonify({"success": True})

@app.route("/api/bid", methods=["POST"])
def api_bid():
    req = request.json or {}
    amount = req.get("amount")
    if not amount:
        return jsonify({"success": False, "error": "Введите сумму"})
    with get_db() as conn:
        row = conn.execute("SELECT id, price FROM auction ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return jsonify({"success": False, "error": "Аукцион неактивен"})
        if int(amount) <= row["price"]:
            return jsonify({"success": False, "error": "Ставка должна быть выше текущей"})
        conn.execute("UPDATE auction SET price = ? WHERE id = ?", (int(amount), row["id"]))
        conn.commit()
    add_log(f"Сделана ставка {amount} ₽ на аукционе")
    return jsonify({"success": True})

@app.route("/api/auction/end", methods=["POST"])
def api_auction_end():
    with get_db() as conn:
        conn.execute("DELETE FROM auction")
        conn.commit()
    add_log("Аукцион завершен")
    return jsonify({"success": True})

@app.route("/api/protocol", methods=["POST"])
def api_protocol():
    req = request.json or {}
    plate = req.get("plate")
    ptype = req.get("type")
    desc = req.get("desc")
    if not plate or not desc:
        return jsonify({"success": False, "error": "Заполните все поля"})
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_db() as conn:
        conn.execute("INSERT INTO history (plate, type, desc, date) VALUES (?, ?, ?, ?)", (plate, ptype, desc, date_str))
        conn.commit()
    add_log(f"Составлен протокол ({ptype}) для т/с {plate}")
    return jsonify({"success": True})

@app.route("/api/wanted", methods=["POST"])
def api_wanted():
    req = request.json or {}
    plate = req.get("plate")
    reason = req.get("reason")
    if not plate or not reason:
        return jsonify({"success": False, "error": "Заполните все поля"})
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO wanted (plate, reason) VALUES (?, ?)", (plate, reason))
        conn.execute("INSERT INTO history (plate, type, desc, date) VALUES (?, ?, ?, ?)", (plate, "РОЗЫСК", reason, date_str))
        conn.commit()
    add_log(f"Транспорт {plate} объявлен в розыск: {reason}")
    return jsonify({"success": True})

@app.route("/api/unwanted", methods=["POST"])
def api_unwanted():
    req = request.json or {}
    plate = req.get("plate")
    if not plate:
        return jsonify({"success": False, "error": "Не указан номер"})
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_db() as conn:
        conn.execute("DELETE FROM wanted WHERE plate = ?", (plate,))
        conn.execute("INSERT INTO history (plate, type, desc, date) VALUES (?, ?, ?, ?)", (plate, "СНЯТ С РОЗЫСКА", "Розыск аннулирован", date_str))
        conn.commit()
    add_log(f"Транспорт {plate} снят с розыска")
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
