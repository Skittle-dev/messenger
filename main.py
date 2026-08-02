import os
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cat_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Данные твоего бота
GMAIL_USER = "catmessagerbot@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD")

verification_codes = {}

def send_verification_code(email, code):
    """Отправка кода прямо от нашего бота"""
    msg = MIMEText(f"Ваш код подтверждения для привязки почты в Cat Messenger: {code}")
    msg['Subject'] = "Код подтверждения Cat Messenger 🐱"
    msg['From'] = f"Cat Bot <{GMAIL_USER}>"
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False

# Твой старый оригинальный интерфейс (Чат + Профиль)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cat Messenger</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #0f172a; color: white; display: flex; height: 100vh; overflow: hidden; }
        
        /* Панель навигации */
        .sidebar { width: 280px; background: #1e293b; border-right: 1px solid #334155; display: flex; flex-direction: column; }
        .logo-box { padding: 20px; font-size: 20px; font-weight: bold; color: #38bdf8; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 10px; }
        .nav-list { flex: 1; padding: 10px 0; }
        .nav-item { padding: 14px 20px; cursor: pointer; border-bottom: 1px solid #1e293b; transition: 0.2s; display: flex; align-items: center; gap: 12px; font-size: 15px; }
        .nav-item:hover, .nav-item.active { background: #334155; color: #38bdf8; }
        
        /* Главное окно */
        .content-area { flex: 1; display: flex; flex-direction: column; background: #0f172a; }
        .tab-page { display: none; width: 100%; height: 100%; flex-direction: column; }
        .tab-page.active { display: flex; }

        /* Вкладка: Чат */
        .header { padding: 18px 24px; background: #1e293b; border-bottom: 1px solid #334155; font-weight: bold; font-size: 18px; }
        .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        .msg { max-width: 70%; padding: 10px 16px; border-radius: 12px; background: #334155; word-break: break-word; line-height: 1.4; }
        .msg-author { font-size: 12px; color: #38bdf8; margin-bottom: 4px; font-weight: bold; }
        .chat-input-bar { padding: 16px 20px; background: #1e293b; display: flex; gap: 10px; border-top: 1px solid #334155; }
        
        /* Вкладка: Профиль */
        .profile-wrapper { padding: 30px; max-width: 550px; }
        .profile-box { background: #1e293b; padding: 24px; border-radius: 14px; border: 1px solid #334155; }
        .profile-title { font-size: 20px; color: #38bdf8; margin-bottom: 20px; font-weight: bold; }
        .form-group { margin-bottom: 18px; }
        .form-group label { display: block; font-size: 13px; color: #94a3b8; margin-bottom: 6px; }
        
        input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 15px; outline: none; }
        input:focus { border-color: #38bdf8; }
        button { padding: 12px 20px; background: #38bdf8; color: #0f172a; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; font-size: 15px; }
        button:hover { background: #7dd3fc; }
        
        .badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-bottom: 10px; }
        .badge-red { background: #ef4444; color: white; }
        .badge-green { background: #22c55e; color: white; }
        .hidden { display: none !important; }
        .status-msg { margin-top: 8px; font-size: 14px; color: #38bdf8; }
    </style>
</head>
<body>

    <!-- Меню слева -->
    <div class="sidebar">
        <div class="logo-box">🐱 Cat Messenger</div>
        <div class="nav-list">
            <div class="nav-item active" onclick="openTab('chat', this)">💬 Общий чат</div>
            <div class="nav-item" onclick="openTab('profile', this)">👤 Профиль</div>
        </div>
    </div>

    <!-- Основной контент -->
    <div class="content-area">
        
        <!-- Страница Чата -->
        <div id="page-chat" class="tab-page active">
            <div class="header">Общий чат</div>
            <div class="chat-messages" id="messages-list"></div>
            <div class="chat-input-bar">
                <input type="text" id="message-text" placeholder="Напишите сообщение..." onkeypress="if(event.key==='Enter') sendMsg()">
                <button onclick="sendMsg()">Отправить</button>
            </div>
        </div>

        <!-- Страница Профиля -->
        <div id="page-profile" class="tab-page">
            <div class="profile-wrapper">
                <div class="profile-box">
                    <div class="profile-title">Настройки аккаунта</div>
                    
                    <div class="form-group">
                        <label>Ваше имя в чате:</label>
                        <input type="text" id="username-input" value="Кот">
                    </div>

                    <div class="form-group">
                        <label>Привязка Email:</label>
                        <div id="email-status-badge" class="badge badge-red">Не привязана</div>
                        
                        <div id="box-email-input">
                            <input type="email" id="email-to-bind" placeholder="Введите ваш Gmail">
                            <button onclick="requestCode()" style="margin-top: 10px; width: 100%;">Отправить код</button>
                        </div>

                        <div id="box-code-input" class="hidden">
                            <input type="text" id="code-to-verify" placeholder="6-значный код" maxlength="6">
                            <button onclick="verifyCode()" style="margin-top: 10px; width: 100%;">Привязать</button>
                        </div>
                        <div class="status-msg" id="status-info"></div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script>
        const socket = io();
        let targetEmail = '';

        function openTab(tabName, element) {
            document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            
            document.getElementById('page-' + tabName).classList.add('active');
            element.classList.add('active');
        }

        function sendMsg() {
            const input = document.getElementById('message-text');
            const user = document.getElementById('username-input').value || 'Аноним';
            if(input.value.trim()) {
                socket.emit('message', { user: user, text: input.value.trim() });
                input.value = '';
            }
        }

        socket.on('message', (data) => {
            const list = document.getElementById('messages-list');
            list.innerHTML += `
                <div class="msg">
                    <div class="msg-author">${data.user}</div>
                    <div>${data.text}</div>
                </div>`;
            list.scrollTop = list.scrollHeight;
        });

        async function requestCode() {
            const email = document.getElementById('email-to-bind').value;
            if(!email) return alert('Введите Email!');
            
            document.getElementById('status-info').innerText = 'Отправка кода...';
            
            const res = await fetch('/api/send-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email })
            });
            const data = await res.json();
            
            if(data.success) {
                targetEmail = email;
                document.getElementById('box-email-input').classList.add('hidden');
                document.getElementById('box-code-input').classList.remove('hidden');
                document.getElementById('status-info').innerText = 'Код отправлен от catmessagerbot@gmail.com!';
            } else {
                document.getElementById('status-info').innerText = 'Ошибка отправки. Проверьте адрес.';
            }
        }

        async function verifyCode() {
            const code = document.getElementById('code-to-verify').value;
            
            const res = await fetch('/api/verify-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: targetEmail, code })
            });
            const data = await res.json();
            
            if(data.success) {
                document.getElementById('box-code-input').classList.add('hidden');
                const badge = document.getElementById('email-status-badge');
                badge.className = 'badge badge-green';
                badge.innerText = 'Привязана: ' + targetEmail;
                document.getElementById('status-info').innerText = 'Почта успешно подтверждена!';
            } else {
                document.getElementById('status-info').innerText = 'Неверный код!';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/send-code', methods=['POST'])
def api_send_code():
    data = request.json
    email = data.get('email')
    if not email:
        return jsonify({'success': False})
    
    code = str(random.randint(100000, 999999))
    verification_codes[email] = code
    
    if send_verification_code(email, code):
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/verify-code', methods=['POST'])
def api_verify_code():
    data = request.json
    email = data.get('email')
    code = data.get('code')
    
    if verification_codes.get(email) == code:
        del verification_codes[email]
        return jsonify({'success': True})
    return jsonify({'success': False})

@socketio.on('message')
def handle_message(data):
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
