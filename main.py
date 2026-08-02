import os
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Настройки Gmail для отправки с catmessagerbot@gmail.com
GMAIL_USER = "catmessagerbot@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD")

verification_codes = {}

def send_verification_code(email, code):
    """Отправка кода подтверждения через наш аккаунт Gmail"""
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #0f172a; color: #ffffff; border-radius: 10px;">
        <h2 style="color: #38bdf8;">🐱 Cat Messenger</h2>
        <p>Ваш код для входа в систему:</p>
        <div style="background-color: #1e293b; padding: 15px; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #38bdf8; text-align: center; border-radius: 8px;">
            {code}
        </div>
        <p style="margin-top: 15px; font-size: 12px; color: #94a3b8;">Если вы не запрашивали этот код, просто проигнорируйте письмо.</p>
    </div>
    """
    
    msg = MIMEText(html_content, 'html')
    msg['Subject'] = "Код подтверждения Cat Messenger 🐱"
    msg['From'] = f"Cat Bot <{GMAIL_USER}>"
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, email, msg.as_string())
        print(f"✅ Письмо успешно отправлено на {email}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки через Gmail: {e}")
        return False

# Тот самый полноценный интерфейс с чатами и красивым дизайном
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
        body { background-color: #0f172a; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; }
        .app-container { display: flex; width: 100vw; height: 100vh; background: #0f172a; }
        
        /* Авторизация */
        .auth-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #0f172a; display: flex; justify-content: center; align-items: center; z-index: 1000; }
        .card { background-color: #1e293b; padding: 30px; border-radius: 16px; width: 100%; max-width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; }
        h2 { margin-bottom: 20px; color: #38bdf8; }
        input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 16px; outline: none; }
        input:focus { border-color: #38bdf8; }
        button { width: 100%; padding: 12px; margin-top: 10px; background: #38bdf8; color: #0f172a; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.2s; }
        button:hover { background: #7dd3fc; }
        .hidden { display: none !important; }
        .status { color: #4ade80; font-size: 14px; margin-top: 10px; }

        /* Интерфейс мессенджера */
        .sidebar { width: 300px; background: #1e293b; border-right: 1px solid #334155; display: flex; flex-direction: column; }
        .sidebar-header { padding: 20px; font-size: 18px; font-weight: bold; color: #38bdf8; border-bottom: 1px solid #334155; }
        .chat-list { flex: 1; overflow-y: auto; }
        .chat-item { padding: 15px 20px; cursor: pointer; border-bottom: 1px solid #334155; transition: 0.2s; }
        .chat-item:hover, .chat-item.active { background: #334155; }
        
        .chat-area { flex: 1; display: flex; flex-direction: column; background: #0f172a; }
        .chat-header { padding: 20px; background: #1e293b; border-bottom: 1px solid #334155; font-weight: bold; }
        .messages-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .message { max-width: 70%; padding: 10px 14px; border-radius: 12px; background: #334155; word-break: break-word; }
        .message.my-message { background: #0284c7; align-self: flex-end; }
        .chat-input-area { padding: 20px; background: #1e293b; display: flex; gap: 10px; border-top: 1px solid #334155; }
        .chat-input-area input { margin: 0; }
        .chat-input-area button { width: 120px; margin: 0; }
    </style>
</head>
<body>

    <!-- Окно входа / регистрации -->
    <div class="auth-overlay" id="auth-screen">
        <div class="card">
            <h2>🐱 Cat Messenger</h2>
            
            <div id="step-email">
                <input type="email" id="email" placeholder="Введите ваш Gmail">
                <button onclick="sendCode()">Получить код</button>
            </div>
            
            <div id="step-code" class="hidden">
                <input type="text" id="code" placeholder="6-значный код из письма" maxlength="6">
                <button onclick="verifyCode()">Подтвердить код</button>
            </div>
            
            <div id="step-register" class="hidden">
                <input type="text" id="username" placeholder="Ваше имя">
                <button onclick="registerUser()">Войти в мессенджер</button>
            </div>
            
            <div class="status" id="status-msg"></div>
        </div>
    </div>

    <!-- Основной интерфейс мессенджера -->
    <div class="app-container hidden" id="messenger-screen">
        <div class="sidebar">
            <div class="sidebar-header">🐱 Чаты</div>
            <div class="chat-list">
                <div class="chat-item active">💬 Общий чат</div>
            </div>
        </div>
        <div class="chat-area">
            <div class="chat-header" id="chat-title">Общий чат</div>
            <div class="messages-box" id="messages"></div>
            <div class="chat-input-area">
                <input type="text" id="msg-input" placeholder="Введите сообщение..." onkeypress="checkEnter(event)">
                <button onclick="sendMessage()">Отправить</button>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let currentEmail = '';
        let currentUsername = '';

        function showStatus(text) { 
            document.getElementById('status-msg').innerText = text; 
        }

        async function sendCode() {
            currentEmail = document.getElementById('email').value;
            if(!currentEmail) return alert('Введите Email!');
            showStatus('Отправка кода с catmessagerbot@gmail.com...');
            
            const res = await fetch('/api/send-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: currentEmail })
            });
            const data = await res.json();
            if(data.success) {
                document.getElementById('step-email').classList.add('hidden');
                document.getElementById('step-code').classList.remove('hidden');
                showStatus('Код отправлен на почту!');
            } else {
                showStatus('Ошибка отправки. Проверьте почту.');
            }
        }

        async function verifyCode() {
            const code = document.getElementById('code').value;
            if(!code) return alert('Введите код!');
            
            const res = await fetch('/api/verify-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: currentEmail, code })
            });
            const data = await res.json();
            if(data.success) {
                document.getElementById('step-code').classList.add('hidden');
                document.getElementById('step-register').classList.remove('hidden');
                showStatus('Код подтверждён! Придумайте имя.');
            } else {
                showStatus('Неверный код!');
            }
        }

        function registerUser() {
            currentUsername = document.getElementById('username').value;
            if(!currentUsername) return alert('Введите имя!');
            
            document.getElementById('auth-screen').classList.add('hidden');
            document.getElementById('messenger-screen').classList.remove('hidden');
        }

        function sendMessage() {
            const input = document.getElementById('msg-input');
            const text = input.value.trim();
            if(text && currentUsername) {
                socket.emit('message', { user: currentUsername, text: text });
                input.value = '';
            }
        }

        function checkEnter(e) {
            if (e.key === 'Enter') sendMessage();
        }

        socket.on('message', (data) => {
            const box = document.getElementById('messages');
            const isMy = data.user === currentUsername;
            box.innerHTML += `<div class="message ${isMy ? 'my-message' : ''}"><b>${data.user}:</b> ${data.text}</div>`;
            box.scrollTop = box.scrollHeight;
        });
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
