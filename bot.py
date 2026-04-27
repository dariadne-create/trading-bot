import yfinance as yf
import pandas as pd
import requests
import os

# ==============================
# 🔐 CONFIG
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ==============================
# 📊 SP500 REAL (sin bloqueo)
# ==============================
def get_sp500():
    try:
        url = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
        df = pd.read_csv(url)
        symbols = df["Symbol"].tolist()

        # Ajuste formato Yahoo
        symbols = [s.replace(".", "-") for s in symbols]

        print(f"SP500 cargado: {len(symbols)} activos")
        return symbols

    except Exception as e:
        print("Error cargando SP500:", e)
        return []

# ==============================
# 📂 TUS ACTIVOS
# ==============================
raw_assets = """
PEGA AQUI TODAS TUS LISTAS COMPLETAS
"""

# ==============================
# 🧹 LIMPIEZA
# ==============================
def clean_tickers(raw):
    tickers = set()

    for t in raw.replace("\n", "").split(","):
        t = t.strip()
        if not t:
            continue

        if "BINANCE:" in t:
            symbol = t.split(":")[1].replace("USDT", "-USD")
        else:
            symbol = t.split(":")[-1]

        symbol = symbol.replace(".", "-")
        tickers.add(symbol)

    return list(tickers)

# ==============================
# 📩 TELEGRAM
# ==============================
def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Faltan credenciales de Telegram")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ==============================
# 📊 INDICADORES
# ==============================
def EMA(series, p):
    return series.ewm(span=p, adjust=False).mean()

def DMI(df):
    high, low, close = df['High'], df['Low'], df['Close']

    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(14).mean()

    di_plus = 100 * (plus_dm.rolling(14).mean() / atr)
    di_minus = 100 * (minus_dm.rolling(14).mean() / atr)

    return di_plus, di_minus

def RSI(series):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def STOCH_RSI(df):
    rsi = RSI(df["Close"])

    min_rsi = rsi.rolling(14).min()
    max_rsi = rsi.rolling(14).max()

    stoch = (rsi - min_rsi) / (max_rsi - min_rsi)

    k = stoch.rolling(3).mean()
    d = k.rolling(3).mean()

    return k, d

def CCI(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    ma = tp.rolling(20).mean()
    md = (tp - ma).abs().rolling(20).mean()
    return (tp - ma) / (0.015 * md)

# ==============================
# 🚀 LOOP PRINCIPAL
# ==============================
tickers = list(set(get_sp500() + clean_tickers(raw_assets)))

signals = []

for i, ticker in enumerate(tickers):
    print(f"{i+1}/{len(tickers)} - {ticker}")

    try:
        df_d = yf.download(ticker, period="6mo", interval="1d", progress=False)
        df_w = yf.download(ticker, period="1y", interval="1wk", progress=False)

        if len(df_d) < 60 or len(df_w) < 20:
            continue

        df_d = df_d.dropna()
        df_w = df_w.dropna()

        # EMAs
        df_d["EMA10"] = EMA(df_d["Close"], 10)
        df_d["EMA55"] = EMA(df_d["Close"], 55)
        df_w["EMA10"] = EMA(df_w["Close"], 10)
        df_w["EMA55"] = EMA(df_w["Close"], 55)

        weekly_bull = df_w["EMA10"].iloc[-1] > df_w["EMA55"].iloc[-1]
        weekly_bear = df_w["EMA55"].iloc[-1] > df_w["EMA10"].iloc[-1]

        # DMI
        di_plus, di_minus = DMI(df_d)

        if pd.isna(di_plus.iloc[-1]) or pd.isna(di_minus.iloc[-1]):
            continue

        di_ok = di_plus.iloc[-1] > di_minus.iloc[-1]

        # 🟢 BASE LONG
        cross_up = (
            df_d["EMA10"].iloc[-2] < df_d["EMA55"].iloc[-2] and
            df_d["EMA10"].iloc[-1] > df_d["EMA55"].iloc[-1]
        )

        if weekly_bull and cross_up and di_ok:
            signals.append(f"{ticker}")

        # 🔵 REBOTE ALCISTA
        trend = df_d["EMA10"].iloc[-1] > df_d["EMA55"].iloc[-1]
        pullback = df_d["Close"].iloc[-2] < df_d["EMA10"].iloc[-2]
        reclaim = df_d["Close"].iloc[-1] > df_d["EMA10"].iloc[-1]

        if weekly_bull and trend and pullback and reclaim and di_ok:
            signals.append(f"{ticker}")

        # 🟣 REBOTE BAJISTA
        k, d = STOCH_RSI(df_w)
        cci = CCI(df_w)
        cci_ma = cci.rolling(20).mean()

        if pd.isna(k.iloc[-1]) or pd.isna(d.iloc[-1]):
            continue

        stoch_cross = k.iloc[-2] < d.iloc[-2] and k.iloc[-1] > d.iloc[-1]
        cci_cross = cci.iloc[-2] < cci_ma.iloc[-2] and cci.iloc[-1] > cci_ma.iloc[-1]

        if weekly_bear and stoch_cross and cci_cross:
            signals.append(f"{ticker}")

    except Exception as e:
        print(f"Error en {ticker}: {e}")

# ==============================
# 📩 FORMATO PRO
# ==============================
MAX = 5

base = []
rebote = []
bajista = []

for s in signals:
    if s not in base and s not in rebote and s not in bajista:
        base.append(s)

mensaje = "📊 SEÑALES DEL DÍA\n\n"

if base:
    mensaje += "🟢 ACTIVOS DETECTADOS\n"
    mensaje += "\n".join(base[:MAX]) + "\n\n"

if not signals:
    mensaje = "Sin señales hoy"

send_telegram(mensaje)
