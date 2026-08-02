import os
import random
import urllib.request
import json
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

registered_users = {}
verification_codes = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cat Messanger</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #0f172a; color: white; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        .header { background-color: #1e293b; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155; height: 60px; }
        .user-info { display: flex; align-items: center; gap: 12px; cursor: pointer; padding: 4px 8px; border-radius: 12px; transition: 0.2s; }
        .user-info:hover { background: #334155; }
        
        .avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; background: #2563eb; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid #3b82f6; flex-shrink: 0; }
        .status-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 4px; }
        .online { background-color: #22c55e; }
        .status-text { font-size: 11px; color: #94a3b8; }

        #verifyModal, #authModal, #profileVerifyModal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #0f172a; z-index: 1000; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; }
        #authModal, #profileVerifyModal { display: none; }
        
        .auth-box { background: #1e293b; border: 1px solid #334155; padding: 25px; border-radius: 20px; width: 100%; max-width: 360px; display: flex; flex-direction: column; gap: 14px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
        
        .auth-icon-3d {
            width: 75px; height: 75px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            border-radius: 22px; display: flex; align-items: center; justify-content: center; font-size: 38px;
            margin: 0 auto 5px auto; box-shadow: 0 15px 25px rgba(37, 99, 235, 0.4), inset 0 2px 4px rgba(255, 255, 255, 0.3);
            transform: perspective(500px) rotateX(10deg) rotateY(-10deg);
        }

        .avatar-upload { position: relative; width: 80px; height: 80px; margin: 0 auto; cursor: pointer; }
        .avatar-upload img, .avatar-upload .placeholder { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; border: 3px solid #2563eb; background: #0f172a; display: flex; align-items: center; justify-content: center; font-size: 30px; }
        .avatar-upload input { display: none; }

        .content-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
        .screen { display: none; flex: 1; flex-direction: column; height: 100%; position: absolute; width: 100%; background: #0f172a; }
        .screen.active { display: flex; }

        .search-box { padding: 12px; background: #1e293b; display: flex; gap: 8px; border-bottom: 1px solid #334155; }
        .search-box input { flex: 1; background: #0f172a; border: 1px solid #334155; padding: 10px 14px; border-radius: 10px; color: white; outline: none; }
        .btn-primary { background: #2563eb; color: white; border: none; padding: 10px 16px; border-radius: 10px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-secondary { background: #334155; color: white; border: none; padding: 10px 16px; border-radius: 10px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-secondary:hover { background: #475569; }
        .btn-danger { background: #ef4444; color: white; border: none; padding: 10px 16px; border-radius: 10px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-danger:hover { background: #dc2626; }

        .chat-list { flex: 1; overflow-y: auto; padding: 10px; }
        .empty-chats { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #64748b; text-align: center; padding: 20px; }
        .chat-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: #1e293b; margin-bottom: 8px; border-radius: 12px; cursor: pointer; }

        .back-btn { background: none; border: none; color: white; font-size: 16px; cursor: pointer; display: flex; align-items: center; gap: 5px; font-weight: bold; }
        .messages-box { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        
        .msg { max-width: 75%; padding: 10px 14px; border-radius: 16px; font-size: 15px; word-wrap: break-word; }
        .msg.me { background-color: #2563eb; align-self: flex-end; border-bottom-right-radius: 2px; }
        .msg.other { background-color: #1e293b; align-self: flex-start; border-bottom-left-radius: 2px; }
        .msg-media { max-width: 100%; border-radius: 12px; margin-top: 5px; display: block; }
        .sticker-msg { font-size: 60px; line-height: 1; padding: 5px; background: none !important; }
        .msg-time { font-size: 10px; opacity: 0.7; margin-top: 4px; text-align: right; }

        .input-bar { background-color: #1e293b; padding: 10px; display: flex; gap: 8px; border-top: 1px solid #334155; position: relative; align-items: center; }
        .input-bar input { flex: 1; background: #0f172a; border: 1px solid #334155; padding: 12px 16px; border-radius: 24px; color: white; outline: none; }
        
        .btn-plus { width: 42px; height: 42px; border-radius: 50%; background: #334155; border: none; color: white; font-size: 22px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; flex-shrink: 0; }
        .btn-plus:hover { background: #2563eb; transform: rotate(90deg); }

        .attach-menu { position: absolute; bottom: 65px; left: 10px; background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 10px; display: none; flex-direction: column; gap: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); z-index: 50; }
        .attach-option { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 10px; cursor: pointer; font-size: 14px; transition: 0.2s; }
        .attach-option:hover { background: #334155; }

        .sticker-picker { position: absolute; bottom: 65px; left: 10px; background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 12px; display: none; grid-template-columns: repeat(4, 1fr); gap: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); z-index: 51; }
        .sticker-item { font-size: 32px; cursor: pointer; text-align: center; transition: 0.2s; }
        .sticker-item:hover { transform: scale(1.2); }

        .profile-card { padding: 25px; display: flex; flex-direction: column; align-items: center; gap: 15px; overflow-y: auto; flex: 1; }
        .field-group { width: 100%; max-width: 350px; display: flex; flex-direction: column; gap: 5px; text-align: left; }
        .field-group label { font-size: 12px; color: #94a3b8; }
        .field-group input { width: 100%; background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 10px; color: white; outline: none; }
        .id-hint { font-size: 11px; margin-top: 2px; }
        .spam-warn { font-size: 11px; color: #f59e0b; margin-top: 5px; line-height: 1.4; }

        .nav-bar { background-color: #1e293b; display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid #334155; height: 60px; }
        .nav-item { color: #94a3b8; text-decoration: none; font-size: 13px; font-weight: 500; display: flex; flex-direction: column; align-items: center; gap: 2px; cursor: pointer; }
        .nav-item.active { color: #2563eb; }
    </style>
</head>
<body>

    <div id="verifyModal">
        <div class="auth-box">
            <div class="auth-icon-3d">🤖</div>
            <h2>Cat Bot Верификация</h2>
            <p style="font-size: 13px; color: #94a3b8;">Введите вашу почту, чтобы получить код подтверждения.</p>
            
            <div id="stepEmail">
                <div class="field-group" style="margin-bottom: 12px;">
                    <label>Электронная почта</label>
                    <input type="email" id="targetEmail" placeholder="example@gmail.com">
                </div>
                <button class="btn-primary" style="width: 100%;" onclick="requestVerificationCode('reg')">Отправить код</button>
            </div>

            <div id="stepCode" style="display:none;">
                <div class="field-group" style="margin-bottom: 12px;">
                    <label>Введите 6-значный код</label>
                    <input type="text" id="enteredCode" placeholder="123456" maxlength="6">
                </div>
                <button class="btn-primary" style="width: 100%;" onclick="verifyCode('reg')">Подтвердить</button>
            </div>
        </div>
    </div>

    <div id="profileVerifyModal">
        <div class="auth-box">
            <div class="auth-icon-3d">🔗</div>
            <h2>Привязка почты</h2>
            <div id="profStepEmail">
                <div class="field-group" style="margin-bottom: 12px;">
                    <label>Новая почта</label>
                    <input type="email" id="profTargetEmail" placeholder="example@gmail.com">
                </div>
                <button class="btn-primary" style="width: 100%;" onclick="requestVerificationCode('prof')">Отправить код</button>
                <button class="btn-secondary" style="width: 100%; margin-top: 6px;" onclick="closeProfileVerify()">Отмена</button>
            </div>
            <div id="profStepCode" style="display:none;">
                <div class="field-group" style="margin-bottom: 12px;">
                    <label>Введите код</label>
                    <input type="text" id="profEnteredCode" placeholder="123456" maxlength="6">
                </div>
                <button class="btn-primary" style="width: 100%;" onclick="verifyCode('prof')">Подтвердить</button>
            </div>
        </div>
    </div>

    <div id="authModal">
        <div class="auth-box">
            <div class="auth-icon-3d">✈️</div>
            <h2>Регистрация</h2>
            <div class="avatar-upload" onclick="document.getElementById('regAvatarInput').click()">
                <div id="regAvatarPlaceholder" class="placeholder">📷</div>
                <img id="regAvatarImg" src="" style="display:none;">
                <input type="file" id="regAvatarInput" accept="image/*" onchange="handleAvatarSelect(this, 'reg')">
            </div>
            <div class="field-group">
                <label>Ваше имя</label>
                <input type="text" id="regName" placeholder="Иван">
            </div>
            <div class="field-group">
                <label>ID</label>
                <input type="text" id="regId" placeholder="@ivan_007" oninput="checkIdAvailability('reg')">
                <div id="regIdStatusHint" class="id-hint"></div>
            </div>
            <button class="btn-primary" onclick="registerUser()">Зарегистрироваться</button>
        </div>
    </div>

    <div class="header">
        <div id="headerLeft" class="user-info" onclick="openProfileScreen()">
            <div id="headerAvatarBox" class="avatar">?</div>
            <div>
                <div id="headerName" style="font-weight: bold; font-size: 15px;">Чаты</div>
                <div class="status-text"><span class="status-dot online"></span><span id="headerSubtext">В сети</span></div>
            </div>
        </div>
    </div>

    <div class="content-area">
        <div id="screenChatsList" class="screen active">
            <div class="search-box">
                <input type="text" id="newChatInput" placeholder="Поиск по ID (@user)...">
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
                    <input type="text" id="editIdInput" oninput="checkIdAvailability('edit')">
                    <div id="editIdStatusHint" class="id-hint"></div>
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
        <div class="nav-item active" onclick="switchScreen('screenChatsList', this)"><span>💬</span> Чаты</div>
        <div class="nav-item" id="navProfileBtn" onclick="switchScreen('screenProfile', this)"><span>👤</span> Профиль</div>
    </div>

    <script>
        const socket = io();
        let myProfile = { name: "", id: "", avatar: "", email: "" };
        let currentChatUser = "";
        let chatsData = {};
        let activeEmailSession = "";

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

        function requestVerificationCode(mode) {
            const email = document.getElementById(mode === 'reg' ? 'targetEmail' : 'profTargetEmail').value.trim();
            if(!email || !email.includes('@')) { alert("Введите почту!"); return; }
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
                    alert("Код отправлен! (Проверьте консоль сервера, если тестируете локально)");
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
            switchScreen('screenProfile', document.getElementById('navProfileBtn'));
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
        function checkIdAvailability(mode) {
            let id = document.getElementById(mode === 'reg' ? 'regId' : 'editIdInput').value.trim();
            const hint = document.getElementById(mode === 'reg' ? 'regIdStatusHint' : 'editIdStatusHint');
            if(!id) { hint.innerText = ''; return; }
            if(!id.startsWith('@')) id = '@' + id;
            if(mode === 'edit' && id === myProfile.id) { hint.innerText = '✓ Ваш ID'; hint.style.color = '#22c55e'; return; }
            socket.emit('check_id_taken', { id }, (res) => {
                hint.innerText = res.taken ? '❌ Занят' : '✓ Свободен';
                hint.style.color = res.taken ? '#ef4444' : '#22c55e';
            });
        }
        function updateHeaderAvatar() {
            const box = document.getElementById('headerAvatarBox');
            if(myProfile.avatar) box.innerHTML = `<img src="${myProfile.avatar}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
            else box.innerText = myProfile.name ? myProfile.name[0].toUpperCase() : '?';
        }
        function switchScreen(id, el) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(id).classList.add('active');
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
                } else { alert("Не найден!"); }
            });
        }
        function renderChatsList() {
            const c = document.getElementById('chatsListContainer'); c.innerHTML = '';
            const keys = Object.keys(chatsData);
            if(keys.length === 0) { c.innerHTML = `<div class="empty-chats">📭 Пусто</div>`; return; }
            keys.forEach(name => {
                const chat = chatsData[name];
                const last = chat.msgs[chat.msgs.length - 1] ? chat.msgs[chat.msgs.length - 1].text : 'Нет сообщений';
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
            document.getElementById('headerLeft').innerHTML = `<div id="headerAvatarBox" class="avatar"></div><div><div style="font-weight:bold;">Чаты</div></div>`;
            updateHeaderAvatar(); renderChatsList(); switchScreen('screenChatsList', document.querySelectorAll('.nav-item')[0]);
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
            socket.emit('send_message', { chat: currentChatUser, user: myProfile.name, avatar: myProfile.avatar, text, type: 'text', time });
            chatsData[currentChatUser].msgs.push({ text, type: 'text', time, is_me: true });
            saveChatsToStorage(); renderMessages(currentChatUser); input.value = '';
        }
        function sendSticker(emoji) {
            const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            socket.emit('send_message', { chat: currentChatUser, user: myProfile.name, avatar: myProfile.avatar, text: emoji, type: 'sticker', time });
            chatsData[currentChatUser].msgs.push({ text: emoji, type: 'sticker', time, is_me: true });
            saveChatsToStorage(); renderMessages(currentChatUser);
        }
        function sendMediaFile(input, type) {
            const file = input.files[0];
            if(file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    socket.emit('send_message', { chat: currentChatUser, user: myProfile.name, avatar: myProfile.avatar, media: e.target.result, type, time });
                    chatsData[currentChatUser].msgs.push({ media: e.target.result, type, time, is_me: true });
                    saveChatsToStorage(); renderMessages(currentChatUser);
                };
                reader.readAsDataURL(file);
            }
        }
        socket.on('receive_message', (data) => {
            if(data.user !== myProfile.name) {
                if(!chatsData[data.user]) chatsData[data.user] = { avatar: data.avatar || "", msgs: [] };
                chatsData[data.user].msgs.push({ text: data.text, media: data.media, type: data.type, time: data.time, is_me: false });
                saveChatsToStorage();
                if(currentChatUser === data.user) renderMessages(data.user);
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
    if not recipient:
        return {'status': 'error', 'message': 'Email не указан'}
    
    code = str(random.randint(100000, 999999))
    verification_codes[recipient] = code
    
    # Безопасный вывод кода в консоль сервера, чтобы можно было сразу войти без ожидания почты
    print(f"\n[CODE FOR {recipient}]: {code}\n")
    
    return {'status': 'ok'}

@socketio.on('check_verify_code')
def handle_check_verify(data):
    recipient = data.get('email')
    code = data.get('code')
    if recipient in verification_codes and verification_codes[recipient] == code:
        del verification_codes[recipient]
        return {'status': 'ok'}
    return {'status': 'error'}

@socketio.on('check_id_taken')
def handle_check_id(data):
    return {'taken': data['id'] in registered_users}

@socketio.on('register_user')
def handle_register(data):
    registered_users[data['id']] = {'name': data['name'], 'avatar': data['avatar'], 'email': data.get('email', '')}
    return {'status': 'ok'}

@socketio.on('update_profile')
def handle_update_profile(data):
    old_id = data['old_id']
    new_id = data['new_id']
    if old_id != new_id and new_id in registered_users:
        return {'status': 'error', 'message': 'ID уже занят'}
    if old_id in registered_users:
        del registered_users[old_id]
    registered_users[new_id] = {'name': data['name'], 'avatar': data['avatar'], 'email': data.get('email', '')}
    return {'status': 'ok'}

@socketio.on('find_user')
def handle_find(data):
    search_id = data['id']
    if search_id in registered_users:
        return {'found': True, 'user': registered_users[search_id]}
    return {'found': False}

@socketio.on('send_message')
def handle_send_message(data):
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
