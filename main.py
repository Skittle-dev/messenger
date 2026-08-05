import os
import io
import random
import smtplib
import requests
import datetime
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template_string, request, jsonify, Response, send_file
from flask_socketio import SocketIO, emit, join_room
from PIL import Image, ImageDraw
import google.generativeai as genai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

# ----------------- НАСТРОЙКИ GEMINI AI И CAT BOT -----------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Каскад моделей Gemini для обхода лимитов
MODELS_CASCADE = [
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-pro'
]

chat_histories = {}

SYSTEM_INSTRUCTION = (
    "Ты — Cat Bot! Тебя создали с помощью моделей Gemini. "
    "Ты являешься главным умным ИИ-помощником в приложении Cat Messenger. "
    "Ты досконально знаешь все функции приложения: чаты, профиль, Cat VPN (веб-прокси), "
    "режим Cat Lite, стикеры, отправку фото и видео. "
    "Если не знаешь ответа, ты ищешь информацию в интернете. "
    "Общайся мило, вежливо, быстро и с кошачьим характером (используй 'Мяу', 🐾 и эмодзи)."
)

def get_cat_bot_response(user_id: str, user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "Мяу! Ошибка: переменная GEMINI_API_KEY не найдена в Environment Variables."

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    chat_histories[user_id].append({"role": "user", "parts": [user_message]})

    if len(chat_histories[user_id]) > 12:
        chat_histories[user_id] = chat_histories[user_id][-12:]

    for model_name in MODELS_CASCADE:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_INSTRUCTION
            )

            response = model.generate_content(chat_histories[user_id])
            bot_text = response.text

            chat_histories[user_id].append({"role": "model", "parts": [bot_text]})
            return bot_text

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota exceeded" in err_str:
                continue
            else:
                print(f"[CatBot Error] {model_name}: {e}")

    if user_id in chat_histories and len(chat_histories[user_id]) > 0:
        chat_histories[user_id].pop()
    return "Прости, мяу... Лимит запросов исчерпан, попробуй чуть позже! 🐾"

# ----------------- ДАННЫЕ БОТА И ПОЧТЫ -----------------
BOT_ID = "@catbot"
BOT_NAME = "Cat Bot (AI)"
CAT_ICON_URL = "https://i.ibb.co/27YwwY44/Screenshot-20260803-011705.jpg"

registered_users = {
    BOT_ID: {'name': BOT_NAME, 'avatar': CAT_ICON_URL, 'email': 'bot@cat.app'}
}
verification_codes = {}

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "catmessagerbot@gmail.com"
SENDER_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

def generate_fallback_icon():
    img = Image.new('RGBA', (192, 192), color=(15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([36, 46, 156, 166], fill=(37, 99, 235))
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

@app.route('/cat-icon.png')
def cat_icon():
    try:
        res = requests.get(CAT_ICON_URL, timeout=5)
        return Response(res.content, mimetype='image/jpeg')
    except Exception:
        return send_file(generate_fallback_icon(), mimetype='image/png')

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "short_name": "Cat Messenger",
        "name": "Cat Messenger App",
        "icons": [{"src": "/cat-icon.png", "type": "image/jpeg", "sizes": "192x192"}],
        "start_url": "/",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "display": "standalone"
    })

@app.route('/sw.js')
def service_worker():
    return Response("self.addEventListener('install', (e) => { self.skipWaiting(); }); self.addEventListener('fetch', (e) => {});", mimetype='application/javascript')

# ----------------- CAT PROXY & LITE ENGINE -----------------
@app.route('/cat-proxy')
def cat_proxy():
    target_url = request.args.get('url')
    lite_mode = request.args.get('lite', 'true') == 'true'

    if not target_url:
        return "Укажите URL", 400

    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(target_url, headers=headers, timeout=10)
        content_type = resp.headers.get('Content-Type', '')

        if lite_mode and 'image' in content_type:
            try:
                img = Image.open(io.BytesIO(resp.content))
                img.thumbnail((400, 400))
                out_io = io.BytesIO()
                img.save(out_io, format='JPEG', quality=40)
                out_io.seek(0)
                return Response(out_io.getvalue(), mimetype='image/jpeg')
            except Exception:
                pass

        response = Response(resp.content, mimetype=content_type)
        response.headers.pop('X-Frame-Options', None)
        response.headers.pop('Content-Security-Policy', None)
        return response

    except Exception as e:
        return f"Ошибка загрузки страницы через Cat Proxy: {str(e)}", 500

def send_email_code(target_email, code):
    if not SENDER_PASSWORD:
        print(f"[Dev Mode] Verification code for {target_email}: {code}")
        return True
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Cat Messenger <{SENDER_EMAIL}>"
        msg['To'] = target_email
        msg['Subject'] = f"Ваш код: {code}"
        msg.attach(MIMEText(f"Ваш код для Cat Messenger: {code}", 'plain', 'utf-8'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, target_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cat Messenger & Proxy</title>
    <link rel="icon" type="image/jpeg" href="/cat-icon.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0f172a">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
        body { background-color: #0f172a; color: white; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .header { background-color: #1e293b; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155; height: 60px; }
        .user-info { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; background: #2563eb; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }
        .status-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; background-color: #22c55e; margin-right: 4px; }
        .status-text { font-size: 11px; color: #94a3b8; }
        #verifyModal, #authModal, #profileVerifyModal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #0f172a; z-index: 1000; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; }
        #authModal, #profileVerifyModal { display: none; }
        .auth-box { background: #1e293b; border: 1px solid #334155; padding: 25px; border-radius: 20px; width: 100%; max-width: 360px; display: flex; flex-direction: column; gap: 14px; text-align: center; }
        .avatar-upload { position: relative; width: 80px; height: 80px; margin: 0 auto; cursor: pointer; }
        .avatar-upload img, .avatar-upload .placeholder { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; border: 3px solid #2563eb; background: #0f172a; display: flex; align-items: center; justify-content: center; font-size: 30px; }
        .avatar-upload input { display: none; }
        .content-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
        .screen { display: none; flex: 1; flex-direction: column; height: 100%; position: absolute; width: 100%; background: #0f172a; }
        .screen.active { display: flex; }
        .search-box { padding: 12px; background: #1e293b; display: flex; gap: 8px; border-bottom: 1px solid #334155; }
        .search-box input { flex: 1; background: #0f172a; border: 1px solid #334155; padding: 10px 14px; border-radius: 10px; color: white; outline: none; }
        .btn-primary { background: #2563eb; color: white; border: none; padding: 10px 16px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .btn-secondary { background: #334155; color: white; border: none; padding: 10px 16px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .btn-danger { background: #ef4444; color: white; border: none; padding: 10px 16px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .chat-list { flex: 1; overflow-y: auto; padding: 10px; }
        .empty-chats { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #64748b; text-align: center; }
        .chat-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: #1e293b; margin-bottom: 8px; border-radius: 12px; cursor: pointer; }
        .back-btn { background: none; border: none; color: white; font-size: 16px; cursor: pointer; display: flex; align-items: center; gap: 5px; font-weight: bold; }
        .messages-box { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        .msg { max-width: 75%; padding: 10px 14px; border-radius: 16px; font-size: 15px; word-wrap: break-word; white-space: pre-wrap; }
        .msg.me { background-color: #2563eb; align-self: flex-end; border-bottom-right-radius: 2px; }
        .msg.other { background-color: #1e293b; align-self: flex-start; border-bottom-left-radius: 2px; }
        .msg-media { max-width: 100%; border-radius: 12px; margin-top: 5px; display: block; }
        .sticker-msg { font-size: 60px; line-height: 1; padding: 5px; background: none !important; }
        .msg-time { font-size: 10px; opacity: 0.7; margin-top: 4px; text-align: right; }
        .input-bar { background-color: #1e293b; padding: 10px; display: flex; gap: 8px; border-top: 1px solid #334155; position: relative; align-items: center; }
        .input-bar input { flex: 1; background: #0f172a; border: 1px solid #334155; padding: 12px 16px; border-radius: 24px; color: white; outline: none; }
        .btn-plus { width: 42px; height: 42px; border-radius: 50%; background: #334155; border: none; color: white; font-size: 22px; cursor: pointer; flex-shrink: 0; }
        .attach-menu { position: absolute; bottom: 65px; left: 10px; background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 10px; display: none; flex-direction: column; gap: 8px; z-index: 50; }
        .attach-option { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 10px; cursor: pointer; font-size: 14px; }
        .sticker-picker { position: absolute; bottom: 65px; left: 10px; background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 12px; display: none; grid-template-columns: repeat(4, 1fr); gap: 10px; z-index: 51; }
        .sticker-item { font-size: 32px; cursor: pointer; text-align: center; }
        .profile-card { padding: 25px; display: flex; flex-direction: column; align-items: center; gap: 15px; overflow-y: auto; flex: 1; }
        .field-group { width: 100%; max-width: 350px; display: flex; flex-direction: column; gap: 5px; text-align: left; }
        .field-group label { font-size: 12px; color: #94a3b8; }
        .field-group input { width: 100%; background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 10px; color: white; outline: none; }
        .nav-bar { background-color: #1e293b; display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid #334155; height: 60px; }
        .nav-item { color: #94a3b8; text-decoration: none; font-size: 13px; font-weight: 500; display: flex; flex-direction: column; align-items: center; gap: 2px; cursor: pointer; }
        .nav-item.active { color: #2563eb; }

        .vpn-container { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 15px; overflow-y: auto; }
        .cat-status { text-align: center; margin-top: 2px; }
        .cat-avatar { font-size: 50px; margin-bottom: 2px; transition: transform 0.3s ease; }
        .status-title { font-size: 16px; font-weight: bold; color: white; }
        .status-sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }
        .power-btn-container { position: relative; display: flex; align-items: center; justify-content: center; margin: 10px 0; }
        .power-btn {
            width: 100px; height: 100px; border-radius: 50%; background: #1e293b; border: 3px solid #334155;
            color: #64748b; font-size: 35px; cursor: pointer; display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4); transition: all 0.3s ease; outline: none;
        }
        .power-btn.active { background: #2563eb; border-color: #60a5fa; color: white; box-shadow: 0 0 35px rgba(37, 99, 235, 0.6); }
        .settings-card { width: 100%; max-width: 360px; background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 10px 12px; margin-bottom: 8px; }
        .card-row { display: flex; align-items: center; justify-content: space-between; }
        .card-info { display: flex; align-items: center; gap: 10px; }
        .card-title { font-size: 13px; font-weight: bold; }
        .card-desc { font-size: 11px; color: #94a3b8; margin-top: 2px; }
        .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #334155; transition: .3s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
        input:checked + .slider { background-color: #2563eb; }
        input:checked + .slider:before { transform: translateX(20px); }
        
        .proxy-browser { width: 100%; max-width: 360px; display: flex; flex-direction: column; gap: 6px; }
        .proxy-browser input { width: 100%; background: #0f172a; border: 1px solid #334155; padding: 9px; border-radius: 10px; color: white; outline: none; font-size: 13px; }
        #proxyFrame { width: 100%; height: 220px; border: 1px solid #334155; border-radius: 12px; background: white; display: none; }
    </style>
</head>
<body>

    <div id="verifyModal">
        <div class="auth-box">
            <div class="avatar" style="width:70px;height:70px;margin:0 auto;"><img src="/cat-icon.png" style="width:100%;height:100%;border-radius:50%;object-fit:cover;"></div>
            <h2>Cat Messenger</h2>
            <p style="font-size: 13px; color: #94a3b8;">Введите почту для входа</p>
            <div id="stepEmail">
                <input type="email" id="targetEmail" placeholder="example@gmail.com" style="width:100%;padding:10px;margin:10px 0;border-radius:8px;background:#0f172a;border:1px solid #334155;color:white;">
                <button class="btn-primary" style="width: 100%;" onclick="requestVerificationCode('reg')">Отправить код</button>
            </div>
            <div id="stepCode" style="display:none;">
                <input type="text" id="enteredCode" placeholder="6-значный код" maxlength="6" style="width:100%;padding:10px;margin:10px 0;border-radius:8px;background:#0f172a;border:1px solid #334155;color:white;">
                <button class="btn-primary" style="width: 100%;" onclick="verifyCode('reg')">Подтвердить</button>
            </div>
        </div>
    </div>

    <div id="profileVerifyModal">
        <div class="auth-box">
            <h2>Привязка почты</h2>
            <div id="profStepEmail">
                <input type="email" id="profTargetEmail" placeholder="example@gmail.com" style="width:100%;padding:10px;margin:10px 0;border-radius:8px;background:#0f172a;border:1px solid #334155;color:white;">
                <button class="btn-primary" style="width: 100%;" onclick="requestVerificationCode('prof')">Отправить код</button>
                <button class="btn-secondary" style="width: 100%; margin-top: 6px;" onclick="closeProfileVerify()">Отмена</button>
            </div>
            <div id="profStepCode" style="display:none;">
                <input type="text" id="profEnteredCode" placeholder="Код" maxlength="6" style="width:100%;padding:10px;margin:10px 0;border-radius:8px;background:#0f172a;border:1px solid #334155;color:white;">
                <button class="btn-primary" style="width: 100%;" onclick="verifyCode('prof')">Подтвердить</button>
            </div>
        </div>
    </div>

    <div id="authModal">
        <div class="auth-box">
            <h2>Регистрация</h2>
            <div class="avatar-upload" onclick="document.getElementById('regAvatarInput').click()">
                <div id="regAvatarPlaceholder" class="placeholder">📷</div>
                <img id="regAvatarImg" src="" style="display:none;">
                <input type="file" id="regAvatarInput" accept="image/*" onchange="handleAvatarSelect(this, 'reg')">
            </div>
            <div class="field-group">
                <label>Имя</label>
                <input type="text" id="regName" placeholder="Ваше имя">
            </div>
            <div class="field-group">
                <label>ID</label>
                <input type="text" id="regId" placeholder="@user">
            </div>
            <button class="btn-primary" onclick="registerUser()">Зарегистрироваться</button>
        </div>
    </div>

    <div class="header">
        <div id="headerLeft" class="user-info" onclick="openProfileScreen()">
            <div id="headerAvatarBox" class="avatar">?</div>
            <div>
                <div id="headerName" style="font-weight: bold; font-size: 15px;">Чаты</div>
                <div class="status-text"><span class="status-dot"></span><span id="headerSubtext">В сети</span></div>
            </div>
        </div>
    </div>

    <div class="content-area">
        <div id="screenChatsList" class="screen active">
            <div class="search-box">
                <input type="text" id="newChatInput" placeholder="Поиск по ID (@user или @catbot)...">
                <button class="btn-primary" onclick="startNewChat()">Найти</button>
            </div>
            <div class="chat-list" id="chatsListContainer"></div>
        </div>

        <div id="screenChatDetail" class="screen">
            <div class="messages-box" id="messagesContainer"></div>
            <div id="attachMenu" class="attach-menu">
                <div class="attach-option" onclick="document.getElementById('filePhotoInput').click()">🖼️ Фото</div>
                <div class="attach-option" onclick="document.getElementById('fileVideoInput').click()">🎥 Видео</div>
                <div class="attach-option" onclick="toggleStickers()">🎭 Стикеры</div>
            </div>
            <input type="file" id="filePhotoInput" accept="image/*" style="display:none;" onchange="sendMediaFile(this, 'image')">
            <input type="file" id="fileVideoInput" accept="video/*" style="display:none;" onchange="sendMediaFile(this, 'video')">
            <div id="stickerPicker" class="sticker-picker">
                <span class="sticker-item" onclick="sendSticker('😎')">😎</span>
                <span class="sticker-item" onclick="sendSticker('🔥')">🔥</span>
                <span class="sticker-item" onclick="sendSticker('🚀')">🚀</span>
                <span class="sticker-item" onclick="sendSticker('❤️')">❤️</span>
                <span class="sticker-item" onclick="sendSticker('🗿')">🗿</span>
                <span class="sticker-item" onclick="sendSticker('👍')">👍</span>
                <span class="sticker-item" onclick="sendSticker('🎉')">🎉</span>
                <span class="sticker-item" onclick="sendSticker('💀')">💀</span>
            </div>
            <form class="input-bar" onsubmit="sendMessage(event)">
                <button type="button" class="btn-plus" onclick="toggleAttachMenu()">+</button>
                <input type="text" id="msgInput" placeholder="Сообщение..." autocomplete="off">
                <button type="submit" class="btn-primary">➤</button>
            </form>
        </div>

        <div id="screenVPN" class="screen">
            <div class="vpn-container">
                <div class="cat-status">
                    <div class="cat-avatar" id="catAvatar">😴</div>
                    <div class="status-title" id="statusTitle">VPN отключен</div>
                    <div class="status-sub" id="statusSub">Нажмите кнопку для подключения Cat Proxy</div>
                </div>

                <div class="power-btn-container">
                    <button class="power-btn" id="vpnBtn" onclick="toggleVPN()">⚡</button>
                </div>

                <div style="width: 100%; max-width: 360px;">
                    <div class="settings-card">
                        <div class="card-row">
                            <div class="card-info">
                                <span style="font-size: 20px;">🇩🇪</span>
                                <div>
                                    <div class="card-title">Германия (Cat Server)</div>
                                    <div class="card-desc">Встроенный веб-прокси</div>
                                </div>
                            </div>
                            <span style="color: #94a3b8;">❯</span>
                        </div>
                    </div>

                    <div class="settings-card">
                        <div class="card-row">
                            <div class="card-info">
                                <span style="font-size: 20px;">🐾</span>
                                <div>
                                    <div class="card-title">Режим Cat Lite</div>
                                    <div class="card-desc">Сжатие медиафайлов</div>
                                </div>
                            </div>
                            <label class="switch">
                                <input type="checkbox" id="catLiteToggle" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>

                    <div class="proxy-browser">
                        <div style="display: flex; gap: 6px;">
                            <input type="text" id="proxyUrl" placeholder="Сайт (например, roblox.com)...">
                            <button class="btn-primary" onclick="openProxySite()">Открыть</button>
                        </div>
                        <iframe id="proxyFrame"></iframe>
                    </div>
                </div>
            </div>
        </div>

        <div id="screenProfile" class="screen">
            <div class="profile-card">
                <div class="avatar-upload" onclick="document.getElementById('editAvatarInput').click()">
                    <div id="editAvatarPlaceholder" class="placeholder">👤</div>
                    <img id="editAvatarImg" src="" style="display:none;">
                    <input type="file" id="editAvatarInput" accept="image/*" onchange="handleAvatarSelect(this, 'edit')">
                </div>
                <div class="field-group">
                    <label>Имя</label>
                    <input type="text" id="editNameInput">
                </div>
                <div class="field-group">
                    <label>ID</label>
                    <input type="text" id="editIdInput">
                </div>
                <div class="field-group">
                    <label>Почта</label>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="editEmailInput" readonly style="opacity: 0.8; cursor: not-allowed;">
                        <button type="button" class="btn-secondary" onclick="openProfileVerify()">Изменить</button>
                    </div>
                </div>
                <button onclick="saveProfileChanges()" class="btn-primary" style="width: 100%; max-width: 350px;">Сохранить</button>
                <button onclick="logoutUser()" class="btn-danger" style="width: 100%; max-width: 350px;">Выйти</button>
            </div>
        </div>
    </div>

    <div class="nav-bar">
        <div class="nav-item active" onclick="switchScreen('screenChatsList', this, 'Чаты')"><span>💬</span> Чаты</div>
        <div class="nav-item" onclick="switchScreen('screenVPN', this, 'Cat VPN')"><span>⚡</span> VPN</div>
        <div class="nav-item" id="navProfileBtn" onclick="switchScreen('screenProfile', this, 'Профиль')"><span>👤</span> Профиль</div>
    </div>

    <script>
        const BOT_NAME = "Cat Bot (AI)";
        const BOT_ID = "@catbot";
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(err => console.log(err));
        }

        const socket = io();
        let myProfile = { name: "", id: "", avatar: "", email: "" };
        let currentChatUser = "";
        let chatsData = {};
        let activeEmailSession = "";
        let isVpnConnected = false;

        window.addEventListener('DOMContentLoaded', () => {
            const savedProfile = localStorage.getItem('messenger_user');
            const savedChats = localStorage.getItem('messenger_chats');
            if (savedChats) { try { chatsData = JSON.parse(savedChats); } catch(e){} }
            if (savedProfile) {
                myProfile = JSON.parse(savedProfile);
                document.getElementById('verifyModal').style.display = 'none';
                socket.emit('register_user', { name: myProfile.name, id: myProfile.id, avatar: myProfile.avatar, email: myProfile.email }, () => { initUserUI(); });
            } else {
                document.getElementById('verifyModal').style.display = 'flex';
            }
        });

        function toggleVPN() {
            const btn = document.getElementById('vpnBtn');
            const title = document.getElementById('statusTitle');
            const sub = document.getElementById('statusSub');
            const avatar = document.getElementById('catAvatar');

            isVpnConnected = !isVpnConnected;

            if (isVpnConnected) {
                btn.classList.add('active');
                avatar.innerText = '😺';
                avatar.style.transform = 'scale(1.1)';
                title.innerText = 'Cat Proxy Включен';
                title.style.color = '#22c55e';
                sub.innerText = 'Защита активна • Веб-трафик шифруется';
            } else {
                btn.classList.remove('active');
                avatar.innerText = '😴';
                avatar.style.transform = 'scale(1)';
                title.innerText = 'VPN отключен';
                title.style.color = 'white';
                sub.innerText = 'Нажмите кнопку для подключения Cat Proxy';
                document.getElementById('proxyFrame').style.display = 'none';
            }
        }

        function openProxySite() {
            if(!isVpnConnected) {
                alert("Сначала включите Cat VPN!");
                return;
            }
            const url = document.getElementById('proxyUrl').value.trim();
            const lite = document.getElementById('catLiteToggle').checked;
            if(!url) return;
            const iframe = document.getElementById('proxyFrame');
            iframe.src = `/cat-proxy?url=${encodeURIComponent(url)}&lite=${lite}`;
            iframe.style.display = 'block';
        }

        function requestVerificationCode(mode) {
            const email = document.getElementById(mode === 'reg' ? 'targetEmail' : 'profTargetEmail').value.trim();
            if(!email || !email.includes('@')) { alert("Введите корректную почту!"); return; }
            activeEmailSession = email;
            socket.emit('send_verify_code', { email: email }, (res) => {
                if(res.status === 'ok') {
                    if(mode === 'reg') {
                        document.getElementById('stepEmail').style.display = 'none';
                        document.getElementById('stepCode').style.display = 'block';
                    } else {
                        document.getElementById('profStepEmail').style.display = 'none';
                        document.getElementById('profStepCode').style.display = 'block';
                    }
                    alert("Код отправлен!");
                } else { alert("Ошибка: " + res.message); }
            });
        }

        function verifyCode(mode) {
            const code = document.getElementById(mode === 'reg' ? 'enteredCode' : 'profEnteredCode').value.trim();
            socket.emit('check_verify_code', { email: activeEmailSession, code: code }, (res) => {
                if(res.status === 'ok') {
                    if(mode === 'reg') {
                        document.getElementById('verifyModal').style.display = 'none';
                        document.getElementById('authModal').style.display = 'flex';
                    } else {
                        myProfile.email = activeEmailSession;
                        document.getElementById('editEmailInput').value = myProfile.email;
                        localStorage.setItem('messenger_user', JSON.stringify(myProfile));
                        closeProfileVerify();
                        alert("Почта изменена!");
                    }
                } else { alert("Неверный код!"); }
            });
        }

        function openProfileVerify() {
            document.getElementById('profStepEmail').style.display = 'block';
            document.getElementById('profStepCode').style.display = 'none';
            document.getElementById('profileVerifyModal').style.display = 'flex';
        }
        function closeProfileVerify() { document.getElementById('profileVerifyModal').style.display = 'none'; }
        function saveChatsToStorage() { localStorage.setItem('messenger_chats', JSON.stringify(chatsData)); }

        function initUserUI() {
            updateHeaderAvatar();
            document.getElementById('authModal').style.display = 'none';
            document.getElementById('verifyModal').style.display = 'none';
            document.getElementById('editNameInput').value = myProfile.name;
            document.getElementById('editIdInput').value = myProfile.id;
            document.getElementById('editEmailInput').value = myProfile.email || "Не привязана";
            if (myProfile.avatar) {
                document.getElementById('editAvatarImg').src = myProfile.avatar;
                document.getElementById('editAvatarImg').style.display = 'block';
                document.getElementById('editAvatarPlaceholder').style.display = 'none';
            }
            renderChatsList();
        }

        function registerUser() {
            const name = document.getElementById('regName').value.trim();
            let id = document.getElementById('regId').value.trim();
            if(!name || !id) { alert("Заполните все поля!"); return; }
            if(!id.startsWith('@')) id = '@' + id;
            myProfile.email = activeEmailSession;
            socket.emit('register_user', { name, id, avatar: myProfile.avatar, email: myProfile.email }, (res) => {
                if(res.status === 'ok') {
                    myProfile.name = name; myProfile.id = id;
                    localStorage.setItem('messenger_user', JSON.stringify(myProfile));
                    initUserUI();
                } else { alert(res.message); }
            });
        }

        function saveProfileChanges() {
            const newName = document.getElementById('editNameInput').value.trim();
            let newId = document.getElementById('editIdInput').value.trim();
            if(!newId.startsWith('@')) newId = '@' + newId;
            socket.emit('update_profile', { old_id: myProfile.id, new_id: newId, name: newName, avatar: myProfile.avatar, email: myProfile.email }, (res) => {
                if(res.status === 'ok') {
                    myProfile.name = newName; myProfile.id = newId;
                    localStorage.setItem('messenger_user', JSON.stringify(myProfile));
                    updateHeaderAvatar(); alert("Сохранено!"); goBackToChats();
                } else { alert(res.message); }
            });
        }

        function logoutUser() {
            if (confirm("Выйти?")) { localStorage.clear(); location.reload(); }
        }

        function toggleAttachMenu() {
            document.getElementById('stickerPicker').style.display = 'none';
            const m = document.getElementById('attachMenu');
            m.style.display = m.style.display === 'flex' ? 'none' : 'flex';
        }
        function toggleStickers() {
            document.getElementById('attachMenu').style.display = 'none';
            const p = document.getElementById('stickerPicker');
            p.style.display = p.style.display === 'grid' ? 'none' : 'grid';
        }
        function openProfileScreen() {
            if(document.getElementById('screenChatDetail').classList.contains('active')) return;
            switchScreen('screenProfile', document.getElementById('navProfileBtn'), 'Профиль');
        }
        function handleAvatarSelect(input, mode) {
            const file = input.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    myProfile.avatar = e.target.result;
                    const img = document.getElementById(mode === 'reg' ? 'regAvatarImg' : 'editAvatarImg');
                    const ph = document.getElementById(mode === 'reg' ? 'regAvatarPlaceholder' : 'editAvatarPlaceholder');
                    img.src = myProfile.avatar; img.style.display = 'block'; ph.style.display = 'none';
                };
                reader.readAsDataURL(file);
            }
        }
        function updateHeaderAvatar() {
            const box = document.getElementById('headerAvatarBox');
            if(myProfile.avatar) box.innerHTML = `<img src="${myProfile.avatar}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
            else box.innerText = myProfile.name ? myProfile.name[0].toUpperCase() : '?';
        }
        function switchScreen(id, el, headerTitle) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(headerTitle) {
                document.getElementById('headerName').innerText = headerTitle;
            }
            if(el) {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                el.classList.add('active');
            }
        }
        function startNewChat() {
            let searchId = document.getElementById('newChatInput').value.trim();
            if(!searchId) return;
            if(!searchId.startsWith('@')) searchId = '@' + searchId;
            socket.emit('find_user', { id: searchId }, (res) => {
                if(res.found) {
                    if(!chatsData[res.user.name]) chatsData[res.user.name] = { avatar: res.user.avatar, msgs: [] };
                    saveChatsToStorage(); renderChatsList(); openChat(res.user.name);
                } else { alert("Пользователь не найден!"); }
            });
        }
        function renderChatsList() {
            const c = document.getElementById('chatsListContainer'); c.innerHTML = '';
            const keys = Object.keys(chatsData);
            if(keys.length === 0) { c.innerHTML = `<div class="empty-chats">📭 Пусто</div>`; return; }
            keys.forEach(name => {
                const chat = chatsData[name];
                const last = chat.msgs[chat.msgs.length - 1] ? (chat.msgs[chat.msgs.length - 1].text || 'Медиафайл') : 'Нет сообщений';
                const div = document.createElement('div');
                div.className = 'chat-item';
                div.innerHTML = `${chat.avatar ? `<img src="${chat.avatar}" class="avatar">` : `<div class="avatar">${name[0]}</div>`}<div><b>${name}</b><div style="font-size:12px;color:#94a3b8">${last}</div></div>`;
                div.onclick = () => openChat(name);
                c.appendChild(div);
            });
        }
        function openChat(name) {
            currentChatUser = name; renderMessages(name); switchScreen('screenChatDetail', null);
            document.getElementById('headerLeft').innerHTML = `<button class="back-btn" onclick="goBackToChats()">⬅</button><b>${name}</b>`;
        }
        function goBackToChats() {
            document.getElementById('headerLeft').innerHTML = `<div id="headerAvatarBox" class="avatar"></div><div><div style="font-weight:bold;" id="headerName">Чаты</div></div>`;
            updateHeaderAvatar(); renderChatsList(); switchScreen('screenChatsList', document.querySelectorAll('.nav-item')[0], 'Чаты');
        }
        function renderMessages(name) {
            const c = document.getElementById('messagesContainer'); c.innerHTML = '';
            (chatsData[name]?.msgs || []).forEach(m => {
                const d = document.createElement('div');
                d.className = `msg ${m.is_me ? 'me' : 'other'} ${m.type === 'sticker' ? 'sticker-msg' : ''}`;
                d.innerHTML = m.type === 'image' ? `<img src="${m.media}" class="msg-media">` : (m.type === 'video' ? `<video src="${m.media}" class="msg-media" controls></video>` : `<div>${m.text}</div><div class="msg-time">${m.time}</div>`);
                c.appendChild(d);
            });
            c.scrollTop = c.scrollHeight;
        }
        function sendMessage(e) {
            e.preventDefault();
            const input = document.getElementById('msgInput');
            const text = input.value.trim();
            if(!text || !currentChatUser) return;
            const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            socket.emit('send_message', { chat: currentChatUser, user: myProfile.name, sender_id: myProfile.id, avatar: myProfile.avatar, text, type: 'text', time });
            chatsData[currentChatUser].msgs.push({ text, type: 'text', time, is_me: true });
            saveChatsToStorage(); renderMessages(currentChatUser); input.value = '';
        }
        function sendSticker(emoji) {
            const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            socket.emit('send_message', { chat: currentChatUser, user: myProfile.name, sender_id: myProfile.id, avatar: myProfile.avatar, text: emoji, type: 'sticker', time });
            chatsData[currentChatUser].msgs.push({ text: emoji, type: 'sticker', time, is_me: true });
            saveChatsToStorage(); renderMessages(currentChatUser);
            document.getElementById('stickerPicker').style.display = 'none';
        }
        function sendMediaFile(input, type) {
            const file = input.files[0];
            if(file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    socket.emit('send_message', { chat: currentChatUser, user: myProfile.name, sender_id: myProfile.id, avatar: myProfile.avatar, media: e.target.result, type, time });
                    chatsData[currentChatUser].msgs.push({ media: e.target.result, type, time, is_me: true });
                    saveChatsToStorage(); renderMessages(currentChatUser);
                };
                reader.readAsDataURL(file);
            }
            document.getElementById('attachMenu').style.display = 'none';
        }
        socket.on('receive_message', (data) => {
            if(data.sender_id !== myProfile.id) {
                const chatName = data.user;
                if(!chatsData[chatName]) chatsData[chatName] = { avatar: data.avatar || "", msgs: [] };
                chatsData[chatName].msgs.push({ text: data.text, media: data.media, type: data.type, time: data.time, is_me: false });
                saveChatsToStorage();
                if(currentChatUser === chatName) renderMessages(chatName);
                renderChatsList();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('send_verify_code')
def handle_send_verify(data):
    recipient = data.get('email')
    if not recipient: return {'status': 'error', 'message': 'Email не указан'}
    code = str(random.randint(100000, 999999))
    verification_codes[recipient] = code
    send_email_code(recipient, code)
    return {'status': 'ok'}

@socketio.on('check_verify_code')
def handle_check_verify(data):
    if verification_codes.get(data.get('email')) == data.get('code'):
        del verification_codes[data.get('email')]
        return {'status': 'ok'}
    return {'status': 'error'}

@socketio.on('register_user')
def handle_register(data):
    user_id = data['id']
    registered_users[user_id] = {'name': data['name'], 'avatar': data['avatar'], 'email': data.get('email', '')}
    join_room(user_id)
    return {'status': 'ok'}

@socketio.on('update_profile')
def handle_update_profile(data):
    registered_users[data['new_id']] = {'name': data['name'], 'avatar': data['avatar'], 'email': data.get('email', '')}
    join_room(data['new_id'])
    return {'status': 'ok'}

@socketio.on('find_user')
def handle_find(data):
    search_id = data['id']
    if search_id in registered_users:
        return {'found': True, 'user': registered_users[search_id]}
    return {'found': False}

@socketio.on('send_message')
def handle_send_message(data):
    target_chat = data.get('chat')
    sender_id = data.get('sender_id')
    
    if target_chat == BOT_NAME or target_chat == BOT_ID:
        user_text = data.get('text', '')
        user_name = data.get('user', 'default_user')

        bot_reply = get_cat_bot_response(user_name, user_text)

        now = datetime.datetime.now().strftime("%H:%M")
        bot_message = {
            'user': BOT_NAME,
            'sender_id': BOT_ID,
            'avatar': CAT_ICON_URL,
            'text': bot_reply,
            'type': 'text',
            'time': now
        }
        emit('receive_message', bot_message, room=sender_id)
    else:
        # Поиск получателя
        target_id = None
        for uid, uinfo in registered_users.items():
            if uinfo['name'] == target_chat:
                target_id = uid
                break
        
        if target_id:
            emit('receive_message', data, room=target_id)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
