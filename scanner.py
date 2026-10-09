import os
import requests
import yfinance as yf
import pandas as pd

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# सुरुवातीची watchlist; यात आणखी पात्र Futures stocks जोडा.
SYMBOLS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN",
    "AXISBANK", "KOTAKBANK", "INFY", "TCS",
    "WIPRO", "LT", "BHARTIARTL", "ITC",
    "TATAMOTORS", "M&M", "MARUTI", "SUNPHARMA",
    "TRENT", "BEL", "HAL", "TATASTEEL",
    "JSWSTEEL", "POWERGRID", "NTPC", "ONGC",
    "ADANIENT", "ADANIPORTS", "COALINDIA", "DLF",
    "BAJFINANCE", "BAJAJFINSV"
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": message},
        timeout=20
    )
    response.raise_for_status()

def scan(symbol):
    ticker = symbol + ".NS"
    df = yf.download(
        ticker, period="7d", interval="15m",
        progress=False, auto_adjust=True
    )

    if df.empty or len(df) < 35:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"].dropna()
    volume = df["Volume"].reindex(close.index).fillna(0)

    if len(close) < 35:
        return None

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1/14, min_periods=14, adjust=False
    ).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1/14, min_periods=14, adjust=False
    ).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))

    # मागील 5 पूर्ण झालेल्या candles चा high
    highs = df["High"].reindex(close.index)
    previous_high = highs.shift(1).rolling(5).max()

    vol_avg = volume.shift(1).rolling(20).mean()

    bullish = (
        (ema20.iloc[-1] > ema50.iloc[-1]) and
        (rsi.iloc[-1] > 60) and
        (close.iloc[-1] > previous_high.iloc[-1]) and
        (volume.iloc[-1] > 1.5 * vol_avg.iloc[-1])
    )

    if bullish:
        return (
            f"🟢 BULLISH SETUP: {symbol}\n"
            f"Price: {close.iloc[-1]:.2f}\n"
            f"RSI: {rsi.iloc[-1]:.1f}\n"
            f"EMA20 > EMA50\n"
            f"5-candle breakout + volume surge\n"
            f"Watchlist alert only — verify before trading."
        )

    return None

for symbol in SYMBOLS:
    try:
        signal = scan(symbol)
        if signal:
            send_telegram(signal)
    except Exception as exc:
        print(f"{symbol}: scan failed: {exc}")
