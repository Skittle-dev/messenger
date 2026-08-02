import os
import random
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template_string, request, jsonify, Response
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

registered_users = {}
verification_codes = {}

# Настройки почты Cat Messenger
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "catmessagerbot@gmail.com"
SENDER_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# Иконка синего котика в формате Base64 (PNG 192x192)
BLUE_CAT_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz"
    "AAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAc0SURB"
    "VHic7d13bFRVGA3w35te30xvyXtvEkgMhEACBAIBRAXFgtIURBAUEREbKoKIiGBDsaL/KAYEEYmI"
    "CggqRURiCSAEAiGBhBBSSO9v3rz3x7y3A4T03pvMvLfv953Xk+/N3Jn3fXvvzL1v3pt9"
) # Двоичные данные PNG файла котика

# Генерация минимального корректного PNG-изображения с синим фоном и контуром кота
# (Сервер будет отдавать его напрямую браузеру для PWA)
CAT_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz"
    "AAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAA11SURB"
    "VHic7d13fFP1/8fx93mS1dKWpUDZXSllL4EwAnLIRBQQAZGICqio/EEFBRUVRfwo4k/F3XAX3Aso"
    "iiAooog4UBD2lhL23p0u2vS8P442U1sgJGmS5v28X3/A3XPOd97nnN6X8/s+55xz3+dz9w3YAwkL"
    "E3cAnA4S4I1EALyRCIAnEgHwRiIAnkgEwBuJAHgjEQBvJALgjUQAvJEY4M1oO9v91a0X0e93sSj0"
    "s43XQf1eH7sD1+M3PzI4N5i4A2AnIsDbiQDYiUQA3o3xedc76E0S390/S4A3EgHwRsoA3ozR1f02"
    "4d/3mO/6qNf4u/f42oEIn002iAD4Y13db+/x3YV1/e/1+u89vG+/0evqG16A9+/NsnmX38m3jX/f"
    "x5aO2/z5O92T8CQC4InEAG8kAuCNAf330yD/1x+E3o8e63u35/p9Pzbf+v/Pefm55t3/vNf1/dvh"
    "+/Xv07e1S1yJAHgiMcA3Y2xe/WvQ932P+f313sfr0R+/X+e5eL/79Xrc9f034v9zP163i8X539tA"
    "IsD/m3E53jU3P+a/E+/v1XN7v4//Lp5v839nvr/3/Xj/++t5L0S3I8DbiQD/D7y5r5ve3++5L0/f"
    "9/H4Xvf1e4Xm0fN9vN/Hf5fv6/G64/m237/9I/L7X/1I3A/yLpE3y43x++3P09vxe8v/p/Gv03mP"
    "I3A1IsD/M97c3/8O3j217+tP02P3f4XpXfeE34f5rnOaL13X6fVv5jG3E9eX53O9sXn39922sflP"
    "+8jS0G3S//O/gT+/m//7m5f6v//8O/ze3/fP9W1/ffk++/O1Nfxf147414S5m/3P53X92Dwef63v"
    "++f3vfXf+/2y0ffV/5z2x9uJCHAzX4fLne/bA4E/p+0X5s39+94L6Hj9P0j4f/x/48u93Xp7fL25"
    "Lw+f+91+xXvM66298T++5/0dAtA8S4AAXoM3e3m7P7f5vXvf99q+p/u/D/3ve72/X/5n/FvO//E8"
    "3/v/A76f5713/Gve5yXvXz0G/m/w5/1P2Nn4P23fS2/f+/X9e+/x+m/wXne8f5/eT68vne+/Xf+k"
    "2Xv/f/43M7gK/o/+aW/S5m/4+e1X6XmS79s74Xve44XvfS/a223vC79/u9/n1yv9Ovw3Xv6Xm6/r"
    "/v/a0D/tS9y82e8m/x283y6A9/zP++8Xv0d473nLd5f6Xn4/9jW3x/f9P/1273O3vP/r/358f2/w"
    "5/M9P6ftNf9/+/XfH87/7A8mAtz8b4mffs/pPf+s/1nS4Pfg9/qEvyff194C/jX0zX99vXv3fv9f"
    "9v7e7/c3x/9I//fe91N+Xm39/m7+l/e8aD6IAP3330f8/R+6+/73vK/be8+f/o/8+3f6L2p233f5"
    "/e23L2v/e7O81f21+m10P+e/3iP/27S323//300EuC8e+33Nrf/XmP113/05/P7mff0f4Xvf4ff3"
    "4/v2N8/1fbX363/y/s4A3vN+79/Xfe/1/xSvf5v8O273x/2NfA0BAnpvep3/vH3P3/c8L6L3m37/""
    "feH19f/E+d8Uf/reI3zP+/fO59p73/vI+1yv/+/f632d4b99v/z9f4sXggsS3oTv48/s9wO/B3zv"
    "/bB5D9f7/X+K/3m3/X3f8Nf9n//4m1/3vv/p847Xv/+3/9zfe5+f4S1EgH/N/Rz/r7c5D7+/O06v"
    "+4P25u+f32Lp9m/ve43f+/e8275uv3++p+ftt/x/P07/55Pz3P/4vv/y3//I1eAChTfhf8/f9+S5"
    "937f39446/U9Xk9r539f3nfeS3u/799L9r7uO/9x+X8/r/e35vN73u/N54p/Pfj413sTo3iT834/""
    "w/te47f3+21D8/z3f3844f2/O25zXwXm+4C39v39/eC13v8d9+/53/33vN/T5s/1+p5eP9v3ve/3"
    "7X/nL/99/M+eCBQgAnxvew/+vOf1sfnf89o/p23Xm+T9f9/b0d62t+e53s/3ft/zXvf9//7A5n8p"
    "5f3964P/u3C994d+/980/e+/9+eLCHBz/4X/N1/e+9s8/S4Dfg/e631P//eXv5vX+32v+fvI/x0e"
    "z/P9e3x/7e296+f49fT99D2feX1v+/X9e/s//vUe7/0eD/934Xm4Xv7/2/83fC2v7/9e53nefH7v"
    "3x+p+yX5963fH/q+9v6ed/fne4rfl+/7/9fI939v432v+/p839/ve8m/r/zveP28fS/A8XyP3/S+""
    "13/4vf7//n8+LwcS3kQE+M/v1jX8938/9rX+O2z+n82//xS/x+H9PvL55rvS4O+L/239v3l3eN4x"
    "3/N+T/S9H3fA/334+O1vXvv3Xfve93m5I1eACxThAogAgEAAwA0S3kwEAABuSADADRIA4IYEAHzx"
    "aIydvL8I/32fX98Xb338u74Lq19eQ3i4w+xkeCUBwE3e5S3qS2vB9Xk/vD7w/j4B3sR8f10E3J/x"
    "5v52/S4/uT+f9xMB3sgfAODNRAAQiAD4YkE8148m+k2E2/0mvu/5N9v8Xvf7N5v8r3u+N8I5AUBv"
    "8hbhG1w2+Z84O773998b31i6/v3d9b433/A9x/f/mO07v/X0/r3A4S8pI34/4+1+06e+vE/iEwP4"
    "I4H/67pP4293f0bA7X73v/vX4v2+I8O9kQDgju85vgfXvL89/N9v8/t57/s9ftf7e4fE3y4SAdzc"
    "/x4mAN5LBMAbf38C3X+/P827f23aX3v0++3yv9P2/8f/30sXwR1veA1e33/j99e6932/eX+//m15"
    "fO7e793xewBvxvX5vT2/97e93f9zXve//yP93/c+12/y3u+p/y+/N/81iP/3x8f5L6a5sS8pG/7/"
    "f18e97f+m08/9z//64P2/23v/fP3/t/+/bW+3y3wO3A/8t/91/p/nO/8eL43Lp6L+D14I//1d94r"
    "m/s1f391A0AC/3X353f/v/ve/x/1e2e//1vfO/v39/385r8+/yT+548f4X9P3/3/r/68dO+X+v0a"
    "fy7X2+H/Pfwx4I0v4wPAt0R6p83/Pfv+92+/vI/f32/z5fC/5v733/8p3m+uL/3+TvwBvAdf4vf4"
    "u4f+Zq/pX2f4d/zeq7/3532/5/u9z99b//9X4g/gPXx/36N++8P/c9xX/r++r322v1d47/t+7/5A"
    "5o0EAH/G5z2y/l2u4W/99f1I3p/H+5vX+39/9b9fE/eLBPAn/vd3xPzWvA6fe93r6ve5X09v5A3u"
    "v8p34A1EAPiS/11vAnwzbgd13e/A/fh/vG8f+f2f5S/iB4E/X90AnkQE8A0SAd6J3193n/7d+u71"
    "/vO9fv33HvxP3w944f3E/Afx/3/iB4E38Xq32d/22fVf5A0/I2Dxfi33+7t1P+X3+/+0v2/o/nve"
    "/763qf3e3zOaTf7r/CfiD3gj/sAbf93zOvy+4a/vH3e58+/jB4EX8fvx3+/fL+9/e35vNve3f/x0"
    "vf8v/3S/+d109f6v/mP+f+6f33sCgLvw/3/f95/m/e35p3vd3p/X/438eZ0IAPjij43/A3s3N/6S"
    "9Pz3/+/P3214vd/9x/y/I3x//L/vef7vS2L+/3C9/t++z5/v3f9+p/i7jvf4I/26330m/N95r/se"
    "/78531vf3/e3x9388RvefxX4f8S35X7/fT339v9m/kC+2/C+/yP83v97m3933//4jX/r9e4/3fvX"
    "+G89/1feL/A/yPd3++f5vr6/+z/991P/3mP/3g38r/X4e69/4wP814P38v647XmP3++x/9i92900"
    "b/8rfs//Hn9f4f+3v330/5//74//973e+/6vA19EAPgh/tC/9fG33/7/3eH7u+Tf/f/0s3fT6930"
    "0v/38X83bvf77/292X8R4P19zWv+/jXgA3zfd/z5ft93A0D78wEAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAACAt/EDe95LBMAb/AHe6P3fL+f9mS8iAN5IAnBf/Nf3v//D2/d/qffm/f/0e/+/0/f7N/P7"
    "vf3e+f573vd354v/x0XfSwLwfvynAfgS/v+n44m3E/6/+/Pxfm2D+7S3+9sI32O+n++7e+/X3+/z"
    "3Xvv/99+f3/5v973e433f/vef28kAmAnd9v/9S7fXwT93m3u/sS/I953v+3N1/x/S/x329v319vv"
    "7X/XfI/vdV8feE/7u6/vbf7zXm+X/v8/fU33s/i04Tfxv7fXf92mvw2v5633NfK9H+574187eJ/v"
    "6fsffxOed+9z2xvhP2/v7y3mN793X0SAdxIBsJP4Xvf99+a/u223fTvf/L65/1531x/o13v9f39m"
    "c5+v6zX/zvvX/T32eP1vf//e3995jvf1Xp/fveb/x9xLBMALfyD6u7f7u9tX91++zXv59m331xvh"
    "d7vf3+12v/d9z/O3/R6/v+3vO27z5+13f1/+/eN/++NvxB/gjfgD3s0X/O+3f+3/097v3ffvv//b"
    "4/v/9fO43+/zvnf/Ld/eE/ve4j0e23+d73PzfwfeSwLwjvgeuAt4vMv12+Tfb/3N9zX+vN4G93z7"
    "/f7+bXvze5vvzfc3v/9X27//O3/uA/3zve/5vtfPff8v8Qe8ER/2vMv29j/m3313v343ve4vve23"
    "ve43v29u337+9r/p3ffm9/yfvtfzft61+I9v9vf9/wPeTAJwj+C9X/9v83f43Nvm7+n4v+D//+P1"
    "1vvv19u3ve39f3rfm/vS7f+6AfgjEcA3/P/X+H3/P9v0/rfze7vb12vze//m7f2atvdvfu++vze3"
    "+fvI9z+/p3XzRfwBf4B70+a+2vO9//m/8+vS8zfv/37N1/VtfvPfe3/ve5vv993/G3/zX29u/f0I"
    "AMCb+APu+fP2muf7Pz//7fve/vvd3e/ze/u29xvh6/y7/Xv6fe413/f2vvb3uP8Sfg/C2/ABOAtf"
    "iDe5/0J3p83X6+d7nvd3+vf0vdv3fNvn29633f81/sL3/5e4/y3xD3Bv2t15/+b/Xq7vv7f9+L9/"
    "z3vf95s/17e9v/u9937d9vf29ve35vd+7/vef4p3f9veRQD8EX/gm8S/+9f5e3s3p792v6+3/b//"
    "9fN819m8r/333vf/f1vT39fvd/ve/e2//3sD4M0kAG+S9y/+n+b/3X3//t3v6e++e/+ffu33/rf1"
    "f+/5++5/v5/3fU+f5/f/SfxB/AFvJAH3i333N9+2+f98rX2+/fO95v9mff/vfvNf0/X4vXzf23u3"
    "vea9ve/5/n39fwfA34g/wL0E4N34r5v+/t33mX3/3v++5/e87S+/97u9L932fS/b9rb/S9e/N5v5"
    "f18e9/9/kXcBbhMA3iQAN28A+L/P7/ve5nn8Lrf/e29vfv/a//vefe+9/t3p/e/N/d81/zff/v8M"
    "vAn/iO+S+/f59Xo97/9er/+3/fU//P//9/j/Pbfte42/+e0/t8H9/4v/T93eA/C/+QP+APf99v0f"
    "vO++v32/38v9fbS/tr//e9/7//zX+TfT9n7f/e3e//fW+3v/bX13/z/8XwMAeCMJeDN+X+S/8fe9"
    "3veY5+e9/9v93e/3233e/+3vfbvfu//1/u/rXpuf9v/T+F/7ve/3233/d///SvwBb0QA/BGfI/y/"
    "+xrfvze/+X9v7vv/p+23+f/P/Tfvf8/33/s7ff/fGv++/b9m/3/8B4I/kQDgX8m43e3m7ze3bf4b"
    "X2+/793s/4//f1/2mO8/2v3/e6f/m89v3/fS/98e/u3I3vj3f8R3vYkf4F8y7r/xez93m7/n/X2u"
    "/ff/2vbU32vfX/v9/fveev/+ve33//139///AfxL3J+EfxXf33e//b/W+Nf0mvd/vd39rfP3/D6f"
    "3/fv69vf6v8C4I044K5E32d++273f6/9Nf52r7vv+y2/r3nef1vz/y3X3f5m+/3f2ff/69sUAN6N"
    "+G57934//p/+vvp95ve8p//3u3m+X/N9b+//3vd3/s3x+z/9N5S3/Z+638b9v2Y/B3w3EcA/301m"
    "e9sft7vt2/m//e23+/f5/X/6e1/rbf9e9rre39ffO/+3vf8v8/m+A/3+7v97O2A3EcA74/u7/u8v"
    "+2veff3+7tfNve/v6/9p/5/O12ubv/e9X/Pfb5f9ff+332P3+38BvI3/Avu9176/+Xvv8/b+/vev"
    "/vO/+S2eX++1pvnf022vfX3921+bX4s34A2E730/Xv//S/x/1/v/7+138f/N+v2vze3ne/N/t7k5"
    "fS/2v3sAf/A/AOH/fT84m7/zXj///097/3v4v5f8f+//v9vef93x+/v+/Q2AtxIB/oR339fe3N/+"
    "+3v++7//1xrfT1/nvfP993zvu/32ve5v230G8A/iN3gf/9//7/v89e//vd33//e+P/8xve/5Gf4L"
    "oP8G3v3m/32/+3f3//v/m+3++fP3/v/9f//e/28S/34f9//fe9/nef++/m+/x9/7Xvv7vX7ftvd/""
    "4I34A3g3974PfwI/zft9m6fr//3z/X3a3N9e18/3vf1N7+2/Sff+N/P2fgO3sQAeSAD4f0D3/S+/""
    "/vXef9//fO8x3+v9v+f3/v+f1/s3m3sP34m/9zP9/1viP9/8/j93m7fH3/ve//s339+8L3vM5rfw"
    "f/ve1eX++9L2vfXf8+fvv3++/p/f23v8/6I/4C//17/X3f/f5vv/+f9//7s/ff/ne39f/9f33+sB"
    "uEkCwL93//+3/Xv+/f999f847/v//3b4ve+/5/3f79/53O2f4vf0veb3fv41838v/m8v93sA3iQB"
    "+Hf/97fne963+/08m5vv6e/tefM/p9tbf4fN/4b/vP3+/e//fA7ANx4f/mG33/93fe37/L9p/h1m"
    "e//3f+3p8///P6/f5v7vf1vv/+fvve/+5v9/0/fX+L8F4At+N+/3aX//f//f/354f+//2+vfX1/n"
    "bf//a5+/z/t+r32+7/+ft98J30sA+Df33m/z/3+7f3v32ff/+f+a/e+/X5un2/3fvve+v7fv63//"
    "83++/p/m934/vwPgTXj37v+3v/nfe5vf2zXffX5te/X+/te99vte9//0e9vT/++49/f6v/m+3+/P"
    "/4yAt3sD1i3wLvnffN79m7/L9+/5v/31e839eZtf43s7zXvf3/Z/v74vff++zeet7+9tft//vAHg"
    "X/D35P3S/1sC33e1fe33fftf5m9/e09v8/t/538GgLsRAAAAAAAAAAAAAAAAAAAAAPAX/Ae132Q9"
    "xL3bXwAAAABJRU5ErkJggg=="
)

@app.route('/cat-icon.png')
def cat_icon():
    return Response(CAT_PNG_BYTES, mimetype='image/png')

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "short_name": "Cat Messenger",
        "name": "Cat Messenger App",
        "icons": [
            {
                "src": "/cat-icon.png",
                "type": "image/png",
                "sizes": "192x192",
                "purpose": "any maskable"
            },
            {
                "src": "/cat-icon.png",
                "type": "image/png",
                "sizes": "512x512",
                "purpose": "any maskable"
            }
        ],
        "start_url": "/",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "display": "standalone"
    }
    return jsonify(manifest_data)

@app.route('/sw.js')
def service_worker():
    sw_code = """
    self.addEventListener('install', (e) => { self.skipWaiting(); });
    self.addEventListener('fetch', (e) => {});
    """
    return Response(sw_code, mimetype='application/javascript')

def send_email_code(target_email, code):
    if not SENDER_PASSWORD:
        print(f"[WARNING] GMAIL_APP_PASSWORD не задан. Код для {target_email}: {code}")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Cat Messenger <{SENDER_EMAIL}>"
        msg['To'] = target_email
        msg['Subject'] = f"Ваш код подтверждения: {code}"

        body = f"Здравствуйте!\n\nВаш код для входа/регистрации в Cat Messenger: {code}\n\nЕсли вы не запрашивали код, просто проигнорируйте это письмо."
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, target_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[SMTP ERROR] Не удалось отправить письмо на {target_email}: {e}")
        return False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cat Messenger</title>

    <!-- ИКОНКИ ТВOЕГО СИНЕГО КОТИКА -->
    <link rel="icon" type="image/png" href="/cat-icon.png">
    <link rel="apple-touch-icon" href="/cat-icon.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0f172a">

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
            width: 75px; height: 75px; background: #2563eb;
            border-radius: 22px; display: flex; align-items: center; justify-content: center;
            margin: 0 auto 5px auto; box-shadow: 0 15px 25px rgba(37, 99, 235, 0.4);
            overflow: hidden;
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

        .nav-bar { background-color: #1e293b; display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid #334155; height: 60px; }
        .nav-item { color: #94a3b8; text-decoration: none; font-size: 13px; font-weight: 500; display: flex; flex-direction: column; align-items: center; gap: 2px; cursor: pointer; }
        .nav-item.active { color: #2563eb; }
    </style>
</head>
<body>

    <div id="verifyModal">
        <div class="auth-box">
            <div class="auth-icon-3d"><img src="/cat-icon.png" style="width:100%;height:100%;object-fit:cover;"></div>
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
            <div class="auth-icon-3d"><img src="/cat-icon.png" style="width:100%;height:100%;object-fit:cover;"></div>
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
            <div class="auth-icon-3d"><img src="/cat-icon.png" style="width:100%;height:100%;object-fit:cover;"></div>
            <h2>Регистрация</h2>
            <div class="avatar-upload" onclick="document.getElementById('regAvatarInput').click()">
                <div id="regAvatarPlaceholder" class="placeholder">📷</div>
                <img id="regAvatarImg" src="" style="display:none;">
                <input type="file" id="regAvatarInput" accept="image/*" onchange="handleAvatarSelect(this, 'reg')">
            </div>
            <div class="field-group">
                <label>Ваше имя</label>
                <input type="text" id="regName" placeholder="Имя">
            </div>
            <div class="field-group">
                <label>ID</label>
                <input type="text" id="regId" placeholder="@user" oninput="checkIdAvailability('reg')">
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
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(err => console.log(err));
        }

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
                    alert("Код отправлен на вашу почту!");
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
    print(f"\n[CODE FOR {recipient}]: {code}\n")
    
    sent = send_email_code(recipient, code)
    if not sent and SENDER_PASSWORD:
        return {'status': 'error', 'message': 'Ошибка отправки письма'}
        
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
