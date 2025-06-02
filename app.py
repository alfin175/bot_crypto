import streamlit as st
st.set_page_config(page_title="Crypto Bullish Dashboard", layout="wide")

import requests
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import time

# ===== CONFIGURABLE =====
RSI_PERIOD = 14
EMA_SHORT = 9
EMA_LONG = 21
VS_CURRENCY = 'usd'
DAYS = 2
TOP_N = 20

# Telegram Bot Config
TELEGRAM_TOKEN = '8070840473:AAFWU2fhpc_kBAPg--cep7pljMiPehjzy4M'
TELEGRAM_CHAT_ID = '6528599397'

# ===== FUNCTIONS =====
def get_coin_ohlc(coin_id, days=DAYS):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {'vs_currency': VS_CURRENCY, 'days': days}
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return []
    return res.json()

def calculate_rsi(prices):
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        if delta > 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))
    avg_gain = sum(gains[-RSI_PERIOD:]) / RSI_PERIOD if gains else 0
    avg_loss = sum(losses[-RSI_PERIOD:]) / RSI_PERIOD if losses else 0
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(prices, period):
    ema = prices[0]
    k = 2 / (period + 1)
    emas = [ema]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
        emas.append(ema)
    return emas

def get_top_coins(n=TOP_N):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': VS_CURRENCY,
        'order': 'market_cap_desc',
        'per_page': n,
        'page': 1,
        'sparkline': False
    }
    res = requests.get(url, params=params)
    return res.json()

def analyze_coin(coin_id):
    data = get_coin_ohlc(coin_id)
    if not data or len(data) < RSI_PERIOD:
        return None
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
    closes = df['close'].tolist()
    rsi = calculate_rsi(closes)
    ema_short = calculate_ema(closes, EMA_SHORT)
    ema_long = calculate_ema(closes, EMA_LONG)

    score = 0
    if rsi < 30:
        score += 1
    if ema_short[-1] > ema_long[-1]:
        score += 1
    if closes[-1] > ema_short[-1]:
        score += 1

    return {
        'coin_id': coin_id,
        'rsi': rsi,
        'ema_short': ema_short[-1],
        'ema_long': ema_long[-1],
        'price': closes[-1],
        'score': score
    }

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, data=data)
    except:
        pass

send_telegram_message("✅ Bot Streamlit berhasil dijalankan.")

# ===== STREAMLIT APP =====
st.title("📈 Crypto Bullish Dashboard with RSI & EMA")

coins = get_top_coins(TOP_N)
coin_options = [coin['id'] for coin in coins]
selected_coin = st.selectbox("Pilih Coin", coin_options)

if selected_coin:
    data = get_coin_ohlc(selected_coin)
    if not data:
        st.error("Gagal mengambil data. Coba coin lain.")
    else:
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['time'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('time', inplace=True)

        prices = df['close'].tolist()
        rsi = calculate_rsi(prices)
        ema_short = calculate_ema(prices, EMA_SHORT)
        ema_long = calculate_ema(prices, EMA_LONG)

        st.subheader(f"{selected_coin.upper()} - Harga Saat Ini: ${prices[-1]:.4f}")
        st.metric("RSI", f"{rsi:.2f}")

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df.index, prices, label='Close Price', color='blue')
        ax.plot(df.index, ema_short, label=f'EMA{EMA_SHORT}', color='green')
        ax.plot(df.index, ema_long, label=f'EMA{EMA_LONG}', color='red')
        ax.set_title("Harga dan EMA")
        ax.legend()
        st.pyplot(fig)

        fig2, ax2 = plt.subplots(figsize=(12, 2))
        rsi_values = [calculate_rsi(prices[:i]) if i > RSI_PERIOD else None for i in range(len(prices))]
        ax2.plot(df.index, rsi_values, label='RSI', color='purple')
        ax2.axhline(70, color='red', linestyle='--')
        ax2.axhline(30, color='green', linestyle='--')
        ax2.set_title("RSI")
        ax2.legend()
        st.pyplot(fig2)

        with st.expander("🔍 Analisa Sinyal Bullish"):
            score = 0
            if rsi < 30:
                st.success("RSI < 30: Oversold")
                score += 1
            if ema_short[-1] > ema_long[-1]:
                st.success("EMA9 > EMA21: Tren naik")
                score += 1
            if prices[-1] > ema_short[-1]:
                st.success("Harga di atas EMA9")
                score += 1

            st.markdown(f"**🔥 Skor Bullish: {score} / 3**")

st.markdown("---")
st.header("🚀 Coin dengan Sinyal Bullish Terkuat")

bullish_results = []
for coin in coins:
    analysis = analyze_coin(coin['id'])
    if analysis and analysis['score'] == 3:
        bullish_results.append(analysis)

if bullish_results:
    df_bullish = pd.DataFrame(bullish_results)
    st.dataframe(df_bullish[['coin_id', 'price', 'rsi', 'ema_short', 'ema_long', 'score']].sort_values(by='score', ascending=False).reset_index(drop=True))

    top_3 = df_bullish.sort_values(by='score', ascending=False).head(3)
    message = "🚀 <b>Top 3 Coin dengan Sinyal Bullish</b>\n"
    for idx, row in top_3.iterrows():
        message += f"\n• <b>{row['coin_id'].upper()}</b> | 💵 ${row['price']:.4f} | RSI: {row['rsi']:.2f}"
    send_telegram_message(message)
else:
    st.info("Tidak ada coin dengan sinyal bullish maksimal saat ini.")
