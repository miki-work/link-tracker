from flask import Flask, request, redirect
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Флаг, чтобы создать таблицу только один раз
_table_initialized = False

def get_db_connection():
    database_url = os.environ["DATABASE_URL"]
    return psycopg2.connect(database_url, sslmode='require')

def init_table_once():
    global _table_initialized
    if _table_initialized:
        return
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
    _table_initialized = True

@app.route('/')
def home():
    return '''
    <h2>🔗 Link Tracker готов!</h2>
    <p>Пример: <a href="/go?to=https://yandex.ru">/go?to=https://yandex.ru</a></p>
    <p><a href="/stats">📊 Статистика</a></p>
    '''

@app.route('/<short_url>')
def track_click(short_url):
    init_table_once()  # Создаём таблицу при первом клике
    target_url = request.args.get('to')
    if not target_url:
        return "Ошибка: нет параметра 'to'", 400

    if request.headers.getlist("X-Forwarded-For"):
        user_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        user_ip = request.remote_addr

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clicks (ip_address, click_time) VALUES (%s, %s)",
            (user_ip, datetime.utcnow())
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Ошибка записи:", e)

    return redirect(target_url)

@app.route('/stats')
def show_stats():
    init_table_once()
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, ip_address, click_time FROM clicks ORDER BY click_time DESC")
        records = cur.fetchall()
        cur.close()
        conn.close()

        html = f"<h2>Кликов: {len(records)}</h2><table border=1><tr><th>ID</th><th>IP</th><th>Время</th></tr>"
        for r in records:
            html += f"<tr><td>{r['id']}</td><td>{r['ip_address']}</td><td>{r['click_time']}</td></tr>"
        html += "</table>"
        return html
    except Exception as e:
        return f"<h2>Ошибка:</h2><pre>{e}</pre>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
