from flask import Flask, request, redirect
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise Exception("❌ Переменная DATABASE_URL не задана")
    # Railway требует sslmode=require
    return psycopg2.connect(database_url, sslmode='require')

def ensure_table_exists():
    """Создаёт таблицу, если её нет. Безопасно вызывать много раз."""
    try:
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
        print("✅ Таблица 'clicks' готова")
    except Exception as e:
        print(f"⚠️ Ошибка при создании таблицы: {e}")

# Создаём таблицу при импорте (а не при первом запросе)
ensure_table_exists()

@app.route('/<short_url>')
def track_click(short_url):
    target_url = request.args.get('to')
    if not target_url:
        return "Ошибка: нет параметра 'to'", 400

    # Получаем реальный IP через прокси Railway
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
        print(f"✅ Записан IP: {user_ip}")
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")

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
            body {{ font-family: -apple-system, sans-serif; padding: 20px; background: #fff; }}
            h2 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 800px; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background: #f8f9fa; }}
            tr:nth-child(even) {{ background: #fcfcfc; }}
        </style></head><body>
        <h2>📊 Статистика кликов (всего: {len(records)})</h2>
        <table>
            <tr><th>ID</th><th>IP-адрес</th><th>Время (UTC)</th></tr>
        """
        for r in records:
            html += f"<tr><td>{r['id']}</td><td>{r['ip_address']}</td><td>{r['click_time']}</td></tr>"
        html += "</table></body></html>"
        return html

    except Exception as e:
        return f"<h2>Ошибка при загрузке статистики:</h2><pre>{e}</pre>"

@app.route('/')
def home():
    return '''
    <h2>🔗 Link Tracker готов!</h2>
    <p>Используй ссылку вида:</p>
    <code>/любое_имя?to=https://любой.сайт</code>
    <p>Пример: <a href="/demo?to=https://yandex.ru">/demo?to=https://yandex.ru</a></p>
    <p><a href="/stats">📊 Посмотреть статистику</a></p>
    '''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
