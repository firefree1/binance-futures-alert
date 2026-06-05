import os
import time
import requests
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

# === KONFIGURASI ===
TELEGRAM_TOKEN = "8747557450:AAEJf8k4q1MQFzs9m7oMIKT5zZlViNqZW20"
CHAT_ID = "7182146237"

def hitung_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def kirim_telegram(pesan):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

def cek_sinyal_koin(symbol):
    url = "https://binance.com"
    params = {"symbol": symbol, "interval": "1h", "limit": 250}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if not data or len(data) < 200:
            return None
        
        close_prices = [float(candle[4]) for candle in data[:-1]]
        
        ema21 = hitung_ema(close_prices, 21)
        ema50 = hitung_ema(close_prices, 50)
        ema200 = hitung_ema(close_prices, 200)
        
        candle_terakhir = data[-2] 
        high = float(candle_terakhir[2])
        low = float(candle_terakhir[3])
        
        terkena = []
        if low <= ema21 <= high: terkena.append(f"EMA 21 ({ema21:.4f})")
        if low <= ema50 <= high: terkena.append(f"EMA 50 ({ema50:.4f})")
        if low <= ema200 <= high: terkena.append(f"EMA 200 ({ema200:.4f})")
        
        if terkena:
            return f"⚠️ *{symbol} (TF 1H)*\nCandle terakhir menyentuh:\n" + "\n".join([f"• {x}" for x in terkena])
    except Exception:
        return None

def proses_scanning():
    print("Memulai scanning koin...")
    url_exchange = "https://binance.com"
    try:
        res = requests.get(url_exchange, timeout=10)
        symbols = [s['symbol'] for s in res.json()['symbols'] if s['symbol'].endswith('USDT') and 'MARGINAL' not in s.get('permissions', [])][:80] 
        # Di Render gratis, kita batasi ke 80 koin teratas agar tidak terkena timeout/overload memory
    except Exception as e:
        print(f"Gagal mengambil daftar koin: {e}")
        return

    for symbol in symbols:
        sinyal = cek_sinyal_koin(symbol)
        if sinyal:
            kirim_telegram(sinyal)
        time.sleep(0.2)
    print("Scanning selesai.")

# Endpoint Web yang akan ditembak oleh UptimeRobot setiap jam
@app.route('/')
def home():
    # Jalankan scanning di background agar web Render langsung merespon dengan cepat
    Thread(target=proses_scanning).start()
    return jsonify({"status": "Scanning dipicu di background", "timestamp": time.time()}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
