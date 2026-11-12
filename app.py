"""
Учебное веб-приложение с двумя намеренно внесёнными уязвимостями:
1) SQL Injection в форме входа;
2) IDOR / Broken Access Control в просмотре профилей.

Запуск: python app.py
Только для локальной лабораторной работы. Не публикуйте уязвимую версию в интернете.
"""
from flask import Flask, request, session, redirect, url_for, render_template_string
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "lab-only-secret-change-me"
DB_PATH = Path(__file__).with_name("lab.db")

LOGIN_PAGE = """
<h1>Вход в систему (уязвимая версия)</h1>
<form method="post">
  <label>Логин <input name="username" required></label><br>
  <label>Пароль <input name="password" type="password" required></label><br>
  <button type="submit">Войти</button>
</form>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
"""

def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL
            )
        """)
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO users (id, username, password, full_name, email) VALUES (?, ?, ?, ?, ?)",
                [
                    (1, "alice", "alice123", "Алиса Иванова", "alice@example.test"),
                    (2, "bob", "bob123", "Борис Петров", "bob@example.test"),
                ],
            )

@app.route("/")
def index():
    if "user_id" in session:
        return (
            f"<h1>Добро пожаловать, {session['username']}!</h1>"
            "<p>Ваш профиль: <a href='/profile/" + str(session["user_id"]) + "'>открыть</a></p>"
            "<p><a href='/logout'>Выйти</a></p>"
        )
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # УЯЗВИМОСТЬ №1: пользовательский ввод напрямую вставляется в SQL.
        query = (
            "SELECT id, username FROM users "
            f"WHERE username = '{username}' AND password = '{password}'"
        )
        with connect_db() as db:
            user = db.execute(query).fetchone()
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        error = "Неверный логин или пароль"
    return render_template_string(LOGIN_PAGE, error=error)

@app.route("/profile/<int:user_id>")
def profile(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    with connect_db() as db:
        user = db.execute(
            "SELECT id, username, full_name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not user:
        return "Пользователь не найден", 404
    # УЯЗВИМОСТЬ №2: не проверяется, принадлежит ли профиль текущему пользователю.
    return (
        f"<h1>Профиль пользователя</h1>"
        f"<p>ID: {user['id']}</p><p>Логин: {user['username']}</p>"
        f"<p>Имя: {user['full_name']}</p><p>Email: {user['email']}</p>"
        "<p><a href='/'>На главную</a></p>"
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
