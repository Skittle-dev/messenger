import os
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Настройки Gmail
GMAIL_USER = "catmessagerbot@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD")  # Берём пароль из Render Environment

registered_users = {}
verification_codes = {}

def send_verification_code(email, code):
    """Отправка 6-значного кода прямо с catmessagerbot@gmail.com"""
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

# HTML Шаблон приложения
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
        body { background-color: #0f172a; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .card { background-color: #1e293b; padding: 25px; border-radius: 16px; width: 100%; max-width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h2 { text-align: center; margin-bottom: 20px; color: #38bdf8; }
        input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 16px; }
        button { width: 100%; padding: 12px; margin-top: 12px; background: #38bdf8; color: #0f172a; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.2s; }
        button:hover { background: #7dd3fc; }
        .hidden { display: none; }
        .chat-box { height: 300px; border: 1px solid #334155; border-radius: 8px; padding: 10px; overflow-y: auto; margin-bottom: 10px; background: #0f172a; }
        .message { margin-bottom: 8px; padding: 6px 10px; border-radius: 6px; background: #334155; }
        .status { color: #4ade80; font-size: 14px; text-align: center; margin-top: 8px; }
    </style>
</head>
<body>
    <div class="card" id="auth-screen">
        <h2>🐱 Cat Messenger</h2>
        <div id="step-email">
            <input type="email" id="email" placeholder="Введите ваш Gmail">
            <button onclick="sendCode()">Получить код</button>
        </div>
        <div id="step-code" class="hidden">
            <input type="text" id="code" placeholder="6-значный код">
            <button onclick="verifyCode()">Подтвердить</button>
        </div>
        <div id="step-register" class="hidden">
            <input type="text" id="username" placeholder="Имя пользователя">
            <input type="text" id="user-tag" placeholder="ID (например @cat)">
            <button onclick="register()">Зарегистрироваться</button>
        </div>
        <div class="status" id="status-msg"></div>
    </div>

    <div class="card hidden" id="chat-screen">
        <h2>Общий Чат</h2>
        <div class="chat-box" id="messages"></div>
        <input type="text" id="msg-input" placeholder="Напишите сообщение...">
        <button onclick="sendMessage()">Отправить</button>
    </div>

    <script>
        const socket = io();
        let currentEmail = '';

        function showStatus(text) { document.getElementById('status-msg').innerText = text; }

        async function sendCode() {
            currentEmail = document.getElementById('email').value;
            if(!currentEmail) return alert('Введите Email!');
            showStatus('Отправка кода...');
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
                showStatus('Ошибка при отправке');
            }
        }

        async function verifyCode() {
            const code = document.getElementById('code').value;
            const res = await fetch('/api/verify-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: currentEmail, code })
            });
            const data = await res.json();
            if(data.success) {
                document.getElementById('step-code').classList.add('hidden');
                document.getElementById('step-register').classList.remove('hidden');
                showStatus('Код подтверждён!');
            } else {
                showStatus('Неверный код');
            }
        }

        function register() {
            const name = document.getElementById('username').value;
            const tag = document.getElementById('user-tag').value;
            if(!name || !tag) return alert('Заполните все поля!');
            document.getElementById('auth-screen').classList.add('hidden');
            document.getElementById('chat-screen').classList.remove('hidden');
        }

        function sendMessage() {
            const input = document.getElementById('msg-input');
            if(input.value) {
                socket.emit('message', input.value);
                input.value = '';
            }
        }

        socket.on('message', (msg) => {
            const box = document.getElementById('messages');
            box.innerHTML += `<div class="message">${msg}</div>`;
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
        return jsonify({'success': False, 'message': 'Email обязателен'})
    
    code = str(random.randint(100000, 999999))
    verification_codes[email] = code
    
    if send_verification_code(email, code):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Не удалось отправить письмо'})

@app.route('/api/verify-code', methods=['POST'])
def api_verify_code():
    data = request.json
    email = data.get('email')
    code = data.get('code')
    

@socketio.on('message')
def handle_message(msg):
    emit('message', msg, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
