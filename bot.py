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
# 📊 SP500 REAL
# ==============================
def get_sp500():
    try:
        url = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
        df = pd.read_csv(url)
        symbols = df["Symbol"].tolist()
        symbols = [s.replace(".", "-") for s in symbols]
        print(f"SP500 cargado: {len(symbols)} activos")
        return symbols
    except Exception as e:
        print("Error cargando SP500:", e)
        return []

# ==============================
# 📂 TUS ACTIVOS (YA INCLUIDOS)
# ==============================
raw_assets = """
BINANCE:AAVEUSDT,BINANCE:ADAUSDT,BINANCE:APTUSDT,BINANCE:ARBUSDT,BINANCE:ATOMUSDT,BINANCE:AVAXUSDT,BINANCE:BCHUSDT,BINANCE:BTCUSDT,BINANCE:DOGEUSDT,BINANCE:DOTUSDT,BINANCE:ETCUSDT,BINANCE:ETHUSDT,BINANCE:FILUSDT,BINANCE:HBARUSDT,BINANCE:INJUSDT,BINANCE:LINKUSDT,BINANCE:LTCUSDT,BINANCE:MANAUSDT,BINANCE:NEARUSDT,BINANCE:NEOUSDT,BINANCE:OPUSDT,BINANCE:POLUSDT,BINANCE:RENDERUSDT,BINANCE:RUNEUSDT,BINANCE:SANDUSDT,BINANCE:SNXUSDT,BINANCE:SOLUSDT,BINANCE:STXUSDT,BINANCE:SUIUSDT,BINANCE:TAOUSDT,BINANCE:THETAUSDT,BINANCE:TONUSDT,BINANCE:UNIUSDT,BINANCE:XRPUSDT,
NASDAQ:WOOF,NYSE:TEVA,NYSE:RKT,NASDAQ:KNDI,NYSE:LDOS,NASDAQ:MGNI,NASDAQ:MSTR,NASDAQ:ESPR,NASDAQ:CRON,NYSE:JMIA,NYSE:CLF,NYSE:SPCE,NYSE:LAC,NYSE:SQM,NYSE:THO,NYSE:WIT,NASDAQ:LGIH,NYSE:NOC,NYSE:RTX,NASDAQ:ERIC,NYSE:GOLD,NASDAQ:LI,NYSE:ENS,NASDAQ:PDD,NASDAQ:FRPT,NASDAQ:CENT,NASDAQ:IDXX,NASDAQ:ROKU,NYSE:LMND,NYSE:NET,NYSE:DT,NASDAQ:UPWK,NASDAQ:RBBN,NYSE:TOL,NYSE:MATX,NYSE:TJX,NASDAQ:NEO,NASDAQ:BILI,NASDAQ:PLUG,NYSE:FLR,NYSE:AMC,NYSE:CNK,NYSE:VST,NASDAQ:TROW,NYSE:URI,NASDAQ:ADP,NYSE:SNAP,NASDAQ:FFIV,NASDAQ:ZS,NASDAQ:FTNT,NASDAQ:LYFT,NYSE:XPEV,NASDAQ:SONO,NYSE:B,NASDAQ:BLDP,NASDAQ:GOGO,NASDAQ:ARRY,NASDAQ:VRSN,NASDAQ:RUN,NASDAQ:CDW,NASDAQ:FIVN,NYSE:THC,NYSE:DGX,NASDAQ:CTAS,NYSE:CTS,NYSE:BLK,NYSE:NOW,NYSE:TYL,NYSE:GWRE,NYSE:PM,NASDAQ:AMAT,NYSE:AZO,NYSE:CLX,NASDAQ:CAKE,NYSE:ABBV,NYSE:EOG,NYSE:LMT,NYSE:COF,NYSE:CVNA,NYSE:EL,NYSE:EQH,NYSE:HCC,NYSE:FICO,NYSE:GRBK,NYSE:TDG,NASDAQ:TXN,NYSE:FLUT,NYSE:EFX,NYSE:NE,NYSE:VAL,NYSE:YETI,NYSE:AER,NASDAQ:CPRT,NYSE:SJM,NYSE:PCG,NYSE:TMO,NASDAQ:BRZE,NASDAQ:WEN,NYSE:EXP,NASDAQ:NSIT,NYSE:ELV,NYSE:AMR,NYSE:ACN,NYSE:KMX,NYSE:EMN,NYSE:JELD,NASDAQ:FLWS,NYSE:LUV,TSX:CCO,NYSE:UAN,NYSE:CVI,NYSE:MOD,NYSE:PBF,NYSE:MTDR,NASDAQ:UEIC,NASDAQ:SAIC,NYSE:HCA,NYSE:SDHC,NYSE:NUVB,NASDAQ:BATRA,NYSE:AS,NASDAQ:CBRL,NYSE:GS,NYSE:VSH,NYSE:CIA,NASDAQ:HTLD,NYSE:IFF,NYSE:AVTR,NYSE:OGN,NASDAQ:DCGO,NYSE:GE,NASDAQ:CROX,NYSE:WAT,NYSE:QSR,NASDAQ:ROP,NYSE:SMRT,NYSE:NSP,NYSE:TROX,NASDAQ:CLAR,NYSE:BSM,NYSE:GLOB,NASDAQ:DLO,NASDAQ:ADPT,NASDAQ:KARO,NASDAQ:METC,NASDAQ:KRNT,NASDAQ:PNTG,NASDAQ:LAKE,NASDAQ:ATRA,NASDAQ:INTU,NASDAQ:WDAY
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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ==============================
# 📊 INDICADORES
# ==============================
def EMA(series, p): return series.ewm(span=p, adjust=False).mean()

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

def RSI(s):
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    return 100 - (100 / (1 + rs))

def STOCH_RSI(df):
    rsi = RSI(df["Close"])
    stoch = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min())
    k = stoch.rolling(3).mean()
    d = k.rolling(3).mean()
    return k, d

def CCI(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    ma = tp.rolling(20).mean()
    md = (tp - ma).abs().rolling(20).mean()
    return (tp - ma) / (0.015 * md)

# ==============================
# 🚀 LOOP
# ==============================
tickers = list(set(get_sp500() + clean_tickers(raw_assets)))
signals = []

for ticker in tickers:
    try:
        df_d = yf.download(ticker, period="6mo", interval="1d", progress=False)
        df_w = yf.download(ticker, period="1y", interval="1wk", progress=False)

        if len(df_d) < 60 or len(df_w) < 20:
            continue

        df_d = df_d.dropna()
        df_w = df_w.dropna()

        df_d["EMA10"] = EMA(df_d["Close"], 10)
        df_d["EMA55"] = EMA(df_d["Close"], 55)
        df_w["EMA10"] = EMA(df_w["Close"], 10)
        df_w["EMA55"] = EMA(df_w["Close"], 55)

        weekly_bull = df_w["EMA10"].iloc[-1] > df_w["EMA55"].iloc[-1]
        weekly_bear = df_w["EMA55"].iloc[-1] > df_w["EMA10"].iloc[-1]

        di_plus, di_minus = DMI(df_d)
        if pd.isna(di_plus.iloc[-1]) or pd.isna(di_minus.iloc[-1]):
            continue

        di_ok = di_plus.iloc[-1] > di_minus.iloc[-1]

        cross_up = df_d["EMA10"].iloc[-2] < df_d["EMA55"].iloc[-2] and df_d["EMA10"].iloc[-1] > df_d["EMA55"].iloc[-1]

        if weekly_bull and cross_up and di_ok:
            signals.append(f"🟢 BASE LONG: {ticker}")

        trend = df_d["EMA10"].iloc[-1] > df_d["EMA55"].iloc[-1]
        pullback = df_d["Close"].iloc[-2] < df_d["EMA10"].iloc[-2]
        reclaim = df_d["Close"].iloc[-1] > df_d["EMA10"].iloc[-1]

        if weekly_bull and trend and pullback and reclaim and di_ok:
            signals.append(f"🔵 REBOTE LONG: {ticker}")

        k, d = STOCH_RSI(df_w)
        cci = CCI(df_w)
        cci_ma = cci.rolling(20).mean()

        if pd.isna(k.iloc[-1]) or pd.isna(d.iloc[-1]):
            continue

        stoch_cross = k.iloc[-2] < d.iloc[-2] and k.iloc[-1] > d.iloc[-1]
        cci_cross = cci.iloc[-2] < cci_ma.iloc[-2] and cci.iloc[-1] > cci_ma.iloc[-1]

        if weekly_bear and stoch_cross and cci_cross:
            signals.append(f"🟣 REBOTE BAJISTA: {ticker}")

    except Exception as e:
        print(f"Error en {ticker}: {e}")

# ==============================
# 📩 FORMATO FINAL
# ==============================
if signals:
    mensaje = "📊 SEÑALES DEL DÍA\n\n"
    mensaje += "\n".join(signals[:10])
else:
    mensaje = "Sin señales hoy"

send_telegram(mensaje)
