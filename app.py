from flask import Flask, request, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

def log_click(ip_address):
    conn = sqlite3.connect('clicks.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            click_time TEXT NOT NULL
        )
    ''')
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO clicks (ip_address, click_time) VALUES (?, ?)", (ip_address, now))
    conn.commit()
    conn.close()

@app.route('/<short_url>')
def track_click(short_url):
    target_url = request.args.get('to')
    if not target_url:
        return "Ошибка: нет параметра 'to'", 400

    # Получаем реальный IP (важно для Railway!)
    if request.headers.getlist("X-Forwarded-For"):
        user_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        user_ip = request.remote_addr

    log_click(user_ip)
    return redirect(target_url)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
