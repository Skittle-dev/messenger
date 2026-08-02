import os
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'catmessanger_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Данные твоего бота для отправки писем
GMAIL_USER = "catmessagerbot@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD")

verification_codes = {}

def send_verification_code(email, code):
    """Отправка 6-значного кода прямо через catmessagerbot@gmail.com"""
    msg = MIMEText(f"Ваш код подтверждения для Cat Messanger: {code}")
    msg['Subject'] = "Код подтверждения Cat Messanger"
    msg['From'] = f"Cat Bot <{GMAIL_USER}>"
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, email, msg.as_string())
        print(f"✅ Код успешно отправлен на {email}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки через Gmail: {e}")
        return False

# Твой родной мобильный интерфейс Cat Messanger
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Cat Messanger</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #121b29; color: #ffffff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        /* Шапка с профилем */
        .app-header { background: #182232; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #232e42; }
        .user-profile-btn { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .avatar-container { position: relative; width: 44px; height: 44px; }
        .avatar { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; background: #253347; }
        .online-dot { position: absolute; bottom: 2px; right: 2px; width: 10px; height: 10px; background: #22c55e; border-radius: 50%; border: 2px solid #182232; }
        .header-info { display: flex; flex-direction: column; }
        .header-title { font-size: 18px; font-weight: 700; color: #ffffff; }
        .header-status { font-size: 13px; color: #22c55e; margin-top: 1px; }

        /* Поиск по ID */
        .search-container { padding: 12px 16px; background: #121b29; display: flex; gap: 10px; }
        .search-input { flex: 1; background: #182232; border: 1px solid #232e42; border-radius: 10px; padding: 10px 14px; color: #fff; font-size: 14px; outline: none; }
        .search-input::placeholder { color: #64748b; }
        .search-btn { background: #2563eb; color: #fff; border: none; border-radius: 10px; padding: 0 18px; font-weight: 600; font-size: 14px; cursor: pointer; }

        /* Список чатов */
        .chats-list { flex: 1; overflow-y: auto; padding: 8px 16px; display: flex; flex-direction: column; gap: 8px; }
        .chat-card { background: #182232; padding: 12px 14px; border-radius: 12px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: 0.2s; }
        .chat-card:active { background: #232e42; }
        .chat-card-avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; }
        .chat-card-details { display: flex; flex-direction: column; gap: 4px; }
        .chat-card-name { font-size: 16px; font-weight: 700; color: #ffffff; }
        .chat-card-sub { font-size: 14px; }

        /* Окно активного чата */
        .chat-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #121b29; display: flex; flex-direction: column; z-index: 100; transform: translateX(100%); transition: transform 0.25s ease; }
        .chat-screen.active { transform: translateX(0); }
        .chat-topbar { background: #182232; padding: 12px 16px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #232e42; }
        .back-btn { background: none; border: none; color: #38bdf8; font-size: 20px; cursor: pointer; padding: 4px; }
        .messages-area { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .message-bubble { max-width: 75%; padding: 10px 14px; border-radius: 14px; background: #182232; font-size: 15px; word-break: break-word; }
        .message-bubble.my-msg { align-self: flex-end; background: #2563eb; }
        .chat-bottom-input { padding: 12px 16px; background: #182232; display: flex; gap: 10px; border-top: 1px solid #232e42; }

        /* Окно профиля / привязки почты */
        .profile-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); display: none; justify-content: center; align-items: center; z-index: 200; padding: 20px; }
        .profile-modal.active { display: flex; }
        .modal-card { background: #182232; width: 100%; max-width: 380px; border-radius: 16px; padding: 20px; border: 1px solid #232e42; position: relative; }
        .modal-close { position: absolute; top: 14px; right: 16px; background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; }
        .modal-title { font-size: 18px; font-weight: 700; margin-bottom: 16px; color: #38bdf8; }
        .modal-field { margin-bottom: 14px; }
        .modal-field label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 6px; }
        
        .modal-input { width: 100%; background: #121b29; border: 1px solid #232e42; border-radius: 8px; padding: 10px 12px; color: #fff; font-size: 14px; outline: none; }
        .modal-btn { width: 100%; background: #2563eb; color: #fff; border: none; border-radius: 8px; padding: 10px; font-weight: 600; cursor: pointer; margin-top: 8px; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
        .badge-red { background: #ef4444; color: #fff; }
        .badge-green { background: #22c55e; color: #fff; }
        .hidden { display: none !important; }
        .status-text { font-size: 13px; color: #38bdf8; margin-top: 8px; }
    </style>
</head>
<body>

    <!-- Шапка -->
    <div class="app-header">
        <div class="user-profile-btn" onclick="openProfile()">
            <div class="avatar-container">
                <img src="https://api.dicebear.com/7.x/bottts/svg?seed=CatUser" class="avatar" alt="Avatar">
                <div class="online-dot"></div>
            </div>
            <div class="header-info">
                <div class="header-title">Чаты</div>
                <div class="header-status">В сети</div>
            </div>
        </div>
    </div>

    <!-- Поиск по ID (@user) -->
    <div class="search-container">
        <input type="text" class="search-input" id="search-id" placeholder="Поиск по ID (@user)...">
        <button class="search-btn">Найти</button>
    </div>

    <!-- Список чатов -->
    <div class="chats-list">
        <div class="chat-card" onclick="openChat('Willie')">
            <img src="https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=100&h=100&fit=crop&crop=faces" class="chat-card-avatar" alt="Willie">
            <div class="chat-card-details">
                <div class="chat-card-name">Willie</div>
                <div class="chat-card-sub">🚀</div>
            </div>
        </div>
    </div>

    <!-- Экран диалога -->
    <div class="chat-screen" id="chat-screen">
        <div class="chat-topbar">
            <button class="back-btn" onclick="closeChat()">←</button>
            <div class="header-title" id="chat-target-name">Чат</div>
        </div>
        <div class="messages-area" id="messages-box"></div>
        <div class="chat-bottom-input">
            <input type="text" class="search-input" id="msg-input" placeholder="Сообщение..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button class="search-btn" onclick="sendMsg()">></button>
        </div>
    </div>

    <!-- Окно Профиля -->
    <div class="profile-modal" id="profile-modal">
        <div class="modal-card">
            <button class="modal-close" onclick="closeProfile()">✕</button>
            <div class="modal-title">Настройки Профиля</div>
            
            <div class="modal-field">
                <label>Ваше имя:</label>
                <input type="text" class="modal-input" id="profile-username" value="Пользователь">
            </div>

            <div class="modal-field">
                <label>Привязка Email:</label>
                <div id="email-badge" class="badge badge-red">Не привязана</div>
                
                <div id="email-step-send">
                    <input type="email" class="modal-input" id="bind-email-input" placeholder="Введите ваш Gmail">
                    <button class="modal-btn" onclick="sendCode()">Отправить код</button>
                </div>

                <div id="email-step-verify" class="hidden">
                    <input type="text" class="modal-input" id="bind-code-input" placeholder="6-значный код" maxlength="6">
                    <button class="modal-btn" onclick="verifyCode()">Подтвердить</button>
                </div>
                <div class="status-text" id="status-info"></div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let currentTarget = '';
        let boundEmail = '';

        function openProfile() {
            document.getElementById('profile-modal').classList.add('active');
        }

        function closeProfile() {
            document.getElementById('profile-modal').classList.remove('active');
        }

        function openChat(name) {
            currentTarget = name;
            document.getElementById('chat-target-name').innerText = name;
            document.getElementById('chat-screen').classList.add('active');
        }

        function closeChat() {
            document.getElementById('chat-screen').classList.remove('active');
        }

        function sendMsg() {
            const input = document.getElementById('msg-input');
            const text = input.value.trim();
            const sender = document.getElementById('profile-username').value || 'Аноним';
            
            if(text) {
                socket.emit('message', { user: sender, text: text });
                input.value = '';
            }
        }

        socket.on('message', (data) => {
            const box = document.getElementById('messages-box');
            const myName = document.getElementById('profile-username').value;
            const isMy = data.user === myName;
            
            box.innerHTML += `<div class="message-bubble ${isMy ? 'my-msg' : ''}"><b>${data.user}:</b> ${data.text}</div>`;
            box.scrollTop = box.scrollHeight;
        });

        async function sendCode() {
            const email = document.getElementById('bind-email-input').value;
            if(!email) return alert('Введите Email!');
            
            document.getElementById('status-info').innerText = 'Отправка кода от catmessagerbot@gmail.com...';
            
            const res = await fetch('/api/send-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email })
            });
            const data = await res.json();
            
            if(data.success) {
                boundEmail = email;
                document.getElementById('email-step-send').classList.add('hidden');
                document.getElementById('email-step-verify').classList.remove('hidden');
                document.getElementById('status-info').innerText = 'Код отправлен на почту!';
            } else {
                document.getElementById('status-info').innerText = 'Ошибка отправки. Проверьте почту.';
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
                document.getElementById('email-step-verify').classList.add('hidden');
                const badge = document.getElementById('email-badge');
                badge.className = 'badge badge-green';
                badge.innerText = 'Привязана: ' + boundEmail;
                document.getElementById('status-info').innerText = 'Почта успешно привязана!';
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
