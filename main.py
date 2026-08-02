import os
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cat_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Настройки для отправки писем строго от нашего бота
GMAIL_USER = "catmessagerbot@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD")

verification_codes = {}

def send_verification_code(email, code):
    """Отправка 6-значного кода прямо от catmessagerbot@gmail.com"""
    msg = MIMEText(f"Ваш код подтверждения для привязки почты в Cat Messenger: {code}")
    msg['Subject'] = "Код подтверждения Cat Messenger 🐱"
    msg['From'] = f"Cat Bot <{GMAIL_USER}>"
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, email, msg.as_string())
        print(f"✅ Код успешно отправлен на {email}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки Gmail: {e}")
        return False

# Твой старый интерфейс с вкладками Чат / Профиль и привязкой почты внутри профиля
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cat Messenger</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
        body { background-color: #0f172a; color: white; display: flex; height: 100vh; overflow: hidden; }
        
        /* Боковое меню */
        .sidebar { width: 260px; background: #1e293b; border-right: 1px solid #334155; display: flex; flex-direction: column; }
        .logo { padding: 20px; font-size: 20px; font-weight: bold; color: #38bdf8; border-bottom: 1px solid #334155; }
        .menu-item { padding: 15px 20px; cursor: pointer; border-bottom: 1px solid #334155; transition: 0.2s; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background: #334155; color: #38bdf8; }
        
        /* Основная зона */
        .main-content { flex: 1; display: flex; flex-direction: column; background: #0f172a; position: relative; }
        .tab-content { display: none; width: 100%; height: 100%; }
        .tab-content.active { display: flex; flex-direction: column; }

        /* Чат */
        .chat-header { padding: 20px; background: #1e293b; border-bottom: 1px solid #334155; font-weight: bold; }
        .messages-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .message { max-width: 70%; padding: 10px 14px; border-radius: 12px; background: #334155; word-break: break-word; }
        .input-area { padding: 20px; background: #1e293b; display: flex; gap: 10px; border-top: 1px solid #334155; }
        
        input { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 16px; outline: none; }
        input:focus { border-color: #38bdf8; }
        button { padding: 12px 20px; background: #38bdf8; color: #0f172a; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #7dd3fc; }

        /* Профиль */
        .profile-container { padding: 40px; max-width: 500px; }
        .profile-card { background: #1e293b; padding: 25px; border-radius: 16px; border: 1px solid #334155; }
        .profile-card h3 { color: #38bdf8; margin-bottom: 15px; }
        .profile-field { margin-bottom: 15px; }
        .profile-field label { display: block; margin-bottom: 5px; color: #94a3b8; font-size: 14px; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; }
        .badge-unverified { background: #ef4444; color: white; }
        .badge-verified { background: #22c55e; color: white; }
        .hidden { display: none !important; }
        .status-text { margin-top: 10px; font-size: 14px; color: #38bdf8; }
    </style>
</head>
<body>

    <!-- Навигация слева -->
    <div class="sidebar">
        <div class="logo">🐱 Cat Messenger</div>
        <div class="menu-item active" onclick="switchTab('chat', this)">💬 Общий чат</div>
        <div class="menu-item" onclick="switchTab('profile', this)">👤 Профиль</div>
    </div>

    <!-- Основной контент -->
    <div class="main-content">
        
        <!-- Вкладка Чата -->
        <div id="tab-chat" class="tab-content active">
            <div class="chat-header">Общий Чат</div>
            <div class="messages-box" id="messages"></div>
            <div class="input-area">
                <input type="text" id="msg-input" placeholder="Напишите сообщение..." onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">Отправить</button>
            </div>
        </div>

        <!-- Вкладка Профиля -->
        <div id="tab-profile" class="tab-content">
            <div class="profile-container">
                <div class="profile-card">
                    <h3>Настройки Профиля</h3>
                    
                    <div class="profile-field">
                        <label>Имя пользователя:</label>
                        <input type="text" id="user-name-input" value="Кот_Пользователь">
                    </div>

                    <div class="profile-field">
                        <label>Привязанная почта:</label>
                        <span id="email-badge" class="badge badge-unverified">Не привязана</span>
                        
                        <div id="email-bind-box" style="margin-top: 10px;">
                            <input type="email" id="bind-email-input" placeholder="Введите ваш Gmail">
                            <button onclick="sendCode()" style="margin-top: 8px; width: 100%;">Отправить код подтверждения</button>
                        </div>

                        <div id="email-code-box" class="hidden" style="margin-top: 10px;">
                            <input type="text" id="bind-code-input" placeholder="6-значный код из письма" maxlength="6">
                            <button onclick="verifyCode()" style="margin-top: 8px; width: 100%;">Подтвердить код</button>
                        </div>
                        <div class="status-text" id="status-msg"></div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script>
        const socket = io();
        let boundEmail = '';

        function switchTab(tabName, element) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            
            document.getElementById('tab-' + tabName).classList.add('active');
            element.classList.add('active');
        }

        function sendMessage() {
            const input = document.getElementById('msg-input');
            const name = document.getElementById('user-name-input').value || 'Аноним';
            if(input.value.trim()) {
                socket.emit('message', { user: name, text: input.value.trim() });
                input.value = '';
            }
        }

        socket.on('message', (data) => {
            const box = document.getElementById('messages');
            box.innerHTML += `<div class="message"><b>${data.user}:</b> ${data.text}</div>`;
            box.scrollTop = box.scrollHeight;
        });

        async function sendCode() {
            const email = document.getElementById('bind-email-input').value;
            if(!email) return alert('Введите Email!');
            
            document.getElementById('status-msg').innerText = 'Отправка кода...';
            
            const res = await fetch('/api/send-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email })
            });
            const data = await res.json();
            
            if(data.success) {
                boundEmail = email;
                document.getElementById('email-bind-box').classList.add('hidden');
                document.getElementById('email-code-box').classList.remove('hidden');
                document.getElementById('status-msg').innerText = 'Код отправлен на почту!';
            } else {
                document.getElementById('status-msg').innerText = 'Ошибка отправки. Проверьте адрес.';
            }
        }

        async function verifyCode() {
            const code = document.getElementById('bind-code-input').value;
            
            const res = await fetch('/api/verify-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: boundEmail, code })
            });
            const data = await res.json();
            
            if(data.success) {
                document.getElementById('email-code-box').classList.add('hidden');
                const badge = document.getElementById('email-badge');
                badge.className = 'badge badge-verified';
                badge.innerText = 'Привязана: ' + boundEmail;
                document.getElementById('status-msg').innerText = 'Почта успешно привязана!';
            } else {
                document.getElementById('status-msg').innerText = 'Неверный код!';
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
