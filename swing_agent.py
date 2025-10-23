import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# === CONFIG ===
TICKERS = ["GOLDBEES.NS", "NIFTYBEES.NS", "ITBEES.NS", "GOLDPETAL.NS"]
EMAIL_FROM = "jeevanantham1989@gmail.com"           # your Gmail
EMAIL_TO = "jeevanantham1989@gmail.com"             # recipient email (can be same)
APP_PASSWORD = "gkbnqakvxrqyygiw"   # Gmail App Password

# === FUNCTION: get swing signal ===
def get_signal(ticker):
    data = yf.download(ticker, period="1mo", interval="1d")
    if data.empty:
        return None

    # Calculate EMA20
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()

    # Pick last row
    last_row = data.iloc[-1]
    last_close = float(last_row["Close"])
    ema20_last = float(last_row["EMA20"])

    # Generate signal
    signal = "BUY" if last_close > ema20_last else "SELL"

    return {
        "ticker": ticker,
        "signal": signal,
        "price": round(last_close, 2)
    }

# === FUNCTION: send email ===
def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.send_message(msg)

# === MAIN ===
if __name__ == "__main__":
    all_signals = []
    for ticker in TICKERS:
        s = get_signal(ticker)
        if s:
            all_signals.append(f"{s['ticker']}: {s['signal']} @ {s['price']}")

    if all_signals:
        body = "\n".join(all_signals)
        subject = f"Swing Trade Signals ({datetime.now().strftime('%Y-%m-%d')})"
        send_email(subject, body)
        print("✅ Email sent!")
    else:
        print("No data or signals today.")
