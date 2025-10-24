from flask import Flask, request, redirect
import os
from datetime import datetime

# Подключаемся к PostgreSQL через переменную DATABASE_URL (Railway сам её задаёт)
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        # Для локальной разработки (если хочешь тестить без Railway)
        raise Exception("DATABASE_URL не задан")
    conn = psycopg2.connect(database_url, sslmode='require')
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id SERIAL PRIMARY KEY,
            ip_address TEXT NOT NULL,
            click_time TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

# Инициализация БД при старте
init_db()

@app.route('/<short_url>')
def track_click(short_url):
    target_url = request.args.get('to')
    if not target_url:
        return "Ошибка: нет параметра 'to'", 400

    # Получаем реальный IP пользователя (важно для прокси, как в Railway)
    if request.headers.getlist("X-Forwarded-For"):
        user_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        user_ip = request.remote_addr

    # Сохраняем клик
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clicks (ip_address, click_time) VALUES (%s, %s)",
        (user_ip, datetime.utcnow())
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(target_url)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

