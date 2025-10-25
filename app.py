from flask import Flask, request, redirect
import os
from datetime import datetime

# Импорты для PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USE_POSTGRES = True
except ImportError:
    USE_POSTGRES = False

app = Flask(__name__)

# === РАБОТА С БАЗОЙ ===
def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise Exception("Переменная DATABASE_URL не задана")
    return psycopg2.connect(database_url, sslmode='require')

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

# === МАРШРУТЫ ===
@app.route('/<short_url>')
def track_click(short_url):
    target_url = request.args.get('to')
    if not target_url:
        return "Ошибка: нет параметра 'to'", 400

    # Получаем реальный IP
    if request.headers.getlist("X-Forwarded-For"):
        user_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        user_ip = request.remote_addr

    # Сохраняем в БД
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
        print(f"Ошибка записи в БД: {e}")

    return redirect(target_url)

@app.route('/stats')
def show_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, ip_address, click_time FROM clicks ORDER BY click_time DESC")
        records = cur.fetchall()
        cur.close()
        conn.close()

        html = f"""
        <html><head><title>Клики</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 800px; }}
            th, td {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
            th {{ background: #f0f0f0; }}
        </style></head><body>
        <h2>Всего кликов: {len(records)}</h2>
        <table>
            <tr><th>ID</th><th>IP</th><th>Время (UTC)</th></tr>
        """
        for r in records:
            html += f"<tr><td>{r['id']}</td><td>{r['ip_address']}</td><td>{r['click_time']}</td></tr>"
        html += "</table></body></html>"
        return html

    except Exception as e:
        return f"<h2>Ошибка:</h2><pre>{e}</pre>"

# === ЗАПУСК ===
if __name__ == '__main__':
    if USE_POSTGRES:
        try:
            init_db()
        except Exception as e:
            print(f"⚠️ БД не инициализирована: {e}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
