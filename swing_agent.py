import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# === CONFIG ===
TICKERS = ["GOLDBEES.NS", "NIFTYBEES.NS", "ITBEES.NS", "GOLDPETAL.NS"]
EMAIL_FROM = "jeevanantham19893@gmail.com"
EMAIL_TO = "jeevanantham19893@gmail.com"
APP_PASSWORD = "gkbn qakv xrqy ygiw"  # from Gmail App Password

def get_signal(ticker):
    data = yf.download(ticker, period="1mo", interval="1d")
    if data.empty:
        return None
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    last_close = data["Close"].iloc[-1]
    ema20_last = data["EMA20"].iloc[-1]
    signal = "BUY" if last_close > ema20_last else "SELL"
    return {"ticker": ticker, "signal": signal, "price": round(last_close, 2)}

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    all_signals = []
    for ticker in TICKERS:
        s = get_signal(ticker)
        if s:
            all_signals.append(f"{s['ticker']}: {s['signal']} @ {s['price']}")

    if all_signals:
        body = "\n".join(all_signals)
        send_email(
            subject=f"Swing Trade Signals ({datetime.now().strftime('%Y-%m-%d')})",
            body=body,
        )
        print("Email sent!")
    else:
        print("No data or signals today.")
