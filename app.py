import os
import secrets
import sqlite3
import hashlib
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, abort

app = Flask(__name__)
app.secret_key = os.environ.get("ROAI_SECRET_KEY") or secrets.token_hex(32)
DB_PATH = os.environ.get("ROAI_DB_PATH", "roai.sqlite3")
ADMIN_USERNAME = os.environ.get("ROAI_ADMIN_USERNAME", "Masya_show")
ADMIN_EMAIL = os.environ.get("ROAI_ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ROAI_ADMIN_PASSWORD", "")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def pw_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()
    return salt + "$" + digest

def pw_ok(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        return secrets.compare_digest(pw_hash(password, salt).split("$", 1)[1], digest)
    except Exception:
        return False

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user', blocked INTEGER NOT NULL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS promo_codes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
            max_uses INTEGER NOT NULL, uses INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1)""")
        columns = [row["name"] for row in c.execute(
            "PRAGMA table_info(promo_codes)"
        ).fetchall()]

        if "reward_text" not in columns:
            c.execute("""
                ALTER TABLE promo_codes
                ADD COLUMN reward_text TEXT NOT NULL DEFAULT 'Поздравляем!'
            """)
        c.execute("""CREATE TABLE IF NOT EXISTS news(
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            body TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            row = c.execute("SELECT id FROM users WHERE username=?", (ADMIN_USERNAME,)).fetchone()
            if not row:
                c.execute("INSERT INTO users(username,email,password_hash,role) VALUES(?,?,?,?)",
                          (ADMIN_USERNAME, ADMIN_EMAIL.lower(), pw_hash(ADMIN_PASSWORD), "admin"))

init_db()

STYLE = """
*{box-sizing:border-box}body{margin:0;background:#090d0b;color:#edf5ef;font:16px Arial,sans-serif}
header{background:#111a14;border-bottom:1px solid #26372b;padding:18px 5%;display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.brand{font-size:21px;font-weight:800;color:#8cf0a3;margin-right:auto}a{color:#9cf0ad;text-decoration:none}
nav{display:flex;gap:18px;flex-wrap:wrap}main{max-width:920px;margin:48px auto;padding:0 18px}
.card{background:#111a14;border:1px solid #26372b;border-radius:16px;padding:24px;margin:16px 0}
h1{font-size:34px}input,textarea{width:100%;padding:13px;margin:7px 0 14px;border-radius:9px;border:1px solid #354b3a;background:#0b120d;color:white}
button{padding:12px 18px;border:0;border-radius:9px;background:#78df91;color:#07110a;font-weight:700;cursor:pointer}
.small{color:#a9b9ad;font-size:14px}.error{color:#ff9b9b}.success{color:#9cf0ad}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #304035}
"""
PAGE = """<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} — Ro AI for favorite</title><style>""" + STYLE + """</style>
<header><div class="brand">Ro AI for favorite</div><nav>
<a href="/">Главная</a><a href="/generate">Генерация</a><a href="/promocodes">Промокоды</a>
{% if session.get('uid') %}<a href="/account">Личный кабинет</a>{% if session.get('role')=='admin' %}<a href="/admin">Админ-панель</a>{% endif %}<a href="/logout">Выйти</a>
{% else %}<a href="/register">Регистрация</a><a href="/login">Вход</a>{% endif %}
</nav></header><main>
{% with messages=get_flashed_messages() %}{% for m in messages %}<p class="success">{{m}}</p>{% endfor %}{% endwith %}
{{ content|safe }}
</main></html>"""

def page(title, content):
    return render_template_string(PAGE, title=title, content=content)

def current_user():
    if not session.get("uid"): return None
    with db() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not current_user(): return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        u=current_user()
        if not u or u["role"]!="admin": abort(403)
        return fn(*a, **kw)
    return wrapped

@app.get("/")

@app.get("/")
def home():
    with db() as c:
        news = c.execute(
            "SELECT * FROM news ORDER BY id DESC"
        ).fetchall()

    news_html = ""
    for item in news:
        news_html += f"""
        <section class="card">
            <h2>{item['title']}</h2>
            <p>{item['body']}</p>
            <p class="small">{item['created_at']}</p>
        </section>
        """

    if not news_html:
        news_html = '<section class="card">Пока новостей нет.</section>'

    return page("Главная", f"""
        <section class="card">
            <h1>Ro AI for favorite</h1>
            <p>Твоя AI-платформа!</p>
        </section>
        <h2>Новости Ro AI</h2>
        {news_html}
    """)

    return page("Главная", """<section class="card"><h1>Твоя AI-платформа</h1>
<p>Добро пожаловать в Ro AI for favorite!</p><p class="small">Создавай, исследуй и следи за новостями проекта.</p>
<a href="/register"><button>Создать аккаунт</button></a></section>
<section class="card"><h2>Новости</h2>Скоро здесь появятся новости Ro AI.</section>""")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        username=request.form.get("username","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if len(username)<3 or "@" not in email or len(password)<8:
            flash("Проверь логин, email и пароль (не менее 8 символов).")
        else:
            try:
                with db() as c:
                    c.execute("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
                              (username,email,pw_hash(password)))
                flash("Аккаунт создан. Теперь войди.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Такой логин или email уже занят.")
    return page("Регистрация", """<section class="card"><h1>Регистрация</h1><form method="post">
<label>Логин</label><input name="username" required minlength="3">
<label>Email</label><input name="email" type="email" required>
<label>Пароль (минимум 8 символов)</label><input name="password" type="password" required minlength="8">
<button>Зарегистрироваться</button></form></section>""")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        identity=request.form.get("identity","").strip()
        with db() as c:
            u=c.execute("SELECT * FROM users WHERE username=? OR email=?",
                        (identity,identity.lower())).fetchone()
        if u and not u["blocked"] and pw_ok(request.form.get("password",""),u["password_hash"]):
            session.clear(); session["uid"]=u["id"]; session["role"]=u["role"]
            return redirect(url_for("account"))
        flash("Неверные данные или аккаунт заблокирован.")
    return page("Вход", """<section class="card"><h1>Вход</h1><form method="post">
<label>Логин или email</label><input name="identity" required>
<label>Пароль</label><input name="password" type="password" required>
<button>Войти</button></form></section>""")

@app.get("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.get("/account")
@login_required
def account():
    u=current_user()
    return page("Личный кабинет", f"""<section class="card"><h1>Личный кабинет</h1>
<p>Привет, <b>{u['username']}</b>!</p><p>Роль: {u['role']}</p></section>""")

@app.get("/generate")
def generate():
    return page("Генерация", """<section class="card"><h1>Генерация</h1>
<h2>СКОРО</h2><p>Раздел генерации появится позже.</p></section>""")

@app.route("/promocodes", methods=["GET","POST"])
@login_required
def promocodes():
    from markupsafe import escape

    message = ""
    modal = ""

    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()

        with db() as c:
            p = c.execute(
                "SELECT * FROM promo_codes WHERE code=? AND active=1",
                (code,)
            ).fetchone()

            if p and p["uses"] < p["max_uses"]:
                c.execute(
                    "UPDATE promo_codes SET uses=uses+1 WHERE id=?",
                    (p["id"],)
                )

                reward = escape(p["reward_text"])

                modal = f"""
                <div class="card" style="
                    position:relative;
                    border:2px solid #78df91;
                    text-align:center;
                    padding:35px;
                    margin-top:25px;
                ">
                    <h1 style="color:#78df91;">🎉 ТЫ ВЫИГРАЛ!</h1>
                    <h2>Поздравляем!</h2>
                    <p style="font-size:20px;">{reward}</p>
                    <button onclick="this.parentElement.remove()">
                        Здорово!
                    </button>
                </div>
                """
            else:
                message = "Промокод недействителен или лимит активаций исчерпан."

    return page("Промокоды", f"""
    <section class="card">
        <h1>Промокоды</h1>
        <p>{escape(message)}</p>
        <form method="post">
            <input name="code" placeholder="Введи промокод" required>
            <button>Активировать</button>
        </form>
    </section>
    {modal}
    """)

@app.route("/admin", methods=["GET","POST"])
@admin_required
def admin():
    with db() as c:
        if request.method == "POST":
            action = request.form.get("action")

            if action == "promo":
                code = request.form.get("code", "").strip().upper()
                reward = request.form.get("reward_text", "").strip()

                try:
                    limit = max(1, int(request.form.get("limit", "1")))
                    if not code or not reward:
                        raise ValueError()

                    c.execute(
                        "INSERT INTO promo_codes(code,max_uses,reward_text) VALUES(?,?,?)",
                        (code, limit, reward)
                    )
                    flash("Промокод создан!")
                except Exception:
                    flash("Не удалось создать промокод. Проверь код и лимит.")

            elif action == "news":
                c.execute(
                    "INSERT INTO news(title,body) VALUES(?,?)",
                    (request.form.get("title", ""), request.form.get("body", ""))
                )
                flash("Новость опубликована.")

            elif action == "toggle":
                c.execute(
                    "UPDATE users SET blocked=1-blocked WHERE id=?",
                    (request.form.get("user_id"),)
                )
                flash("Статус пользователя изменён.")

        users = c.execute(
            "SELECT id,username,email,role,blocked FROM users ORDER BY id"
        ).fetchall()

        promos = c.execute(
            "SELECT * FROM promo_codes ORDER BY id DESC"
        ).fetchall()

    user_rows = "".join(
        f"""<tr>
        <td>{u['username']}</td>
        <td>{u['email']}</td>
        <td>{u['role']}</td>
        <td>{'Заблокирован' if u['blocked'] else 'Активен'}</td>
        <td>
        <form method="post">
        <input type="hidden" name="action" value="toggle">
        <input type="hidden" name="user_id" value="{u['id']}">
        <button>Изменить статус</button>
        </form>
        </td></tr>"""
        for u in users
    )

    promo_rows = "".join(
        f"<tr><td>{p['code']}</td><td>{p['uses']} / {p['max_uses']}</td>"
        f"<td>{'Вкл.' if p['active'] else 'Выкл.'}</td></tr>"
        for p in promos
    )

    return page("Админ-панель", f"""
    <h1>Админ-панель</h1>

    <section class="card">
    <h2>Пользователи</h2>
    <table>
    <tr><th>Логин</th><th>Email</th><th>Роль</th><th>Статус</th><th></th></tr>
    {user_rows}
    </table>
    </section>

    <section class="card">
    <h2>Создать промокод</h2>
    <form method="post">
    <input type="hidden" name="action" value="promo">

    <label>Название промокода</label>
    <input name="code" placeholder="Например ROAI2026" required>

    <label>Лимит активаций</label>
    <input name="limit" type="number" min="1" value="10" required>

    <label>Что выиграл пользователь?</label>
    <textarea name="reward_text" placeholder="Напиши здесь награду или поздравление..." required></textarea>

    <button>Создать промокод</button>
    </form>

    <h3>Созданные промокоды</h3>
    <table>
    <tr><th>Код</th><th>Использовано</th><th>Статус</th></tr>
    {promo_rows}
    </table>
    </section>

    <section class="card">
    <h2>Опубликовать новость</h2>
    <form method="post">
    <input type="hidden" name="action" value="news">
    <input name="title" placeholder="Заголовок" required>
    <textarea name="body" placeholder="Текст новости" required></textarea>
    <button>Опубликовать</button>
    </form>
    </section>
    """)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
