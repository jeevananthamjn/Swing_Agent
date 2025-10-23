import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIG ===
TICKERS = ["GOLDBEES.NS", "NIFTYBEES.NS", "ITBEES.NS", "GOLDPETAL.NS"]
EMAIL_FROM = "jeevanantham1989@gmail.com"           # your Gmail
EMAIL_TO = "jeevanantham1989@gmail.com"             # recipient email
APP_PASSWORD = "gkbn qakv xrqy ygiw"   # Gmail App Password
STOPLOSS_PERCENT = 1.5                       # Stoploss 1.5%
TARGET_PERCENT = 3.0                         # Target 3%

# Google Sheets config
GSHEET_NAME = "SwingSignals"
CREDENTIALS_FILE = "credentials/swingagent-e6b363ab0671.json"

# === GOOGLE SHEETS SETUP ===
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GSHEET_NAME).sheet1  # Use the first sheet

# === FUNCTION: get swing signal ===
def get_signal(ticker):
    data = yf.download(ticker, period="1mo", interval="1h")  # hourly data
    if data.empty:
        return None

    # EMA20
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()

    # Last row
    last_row = data.iloc[-1]
    last_price = float(last_row["Close"])
    ema20 = float(last_row["EMA20"])

    # BUY signal only
    if last_price > ema20:
        signal = "BUY"
        stoploss = last_price * (1 - STOPLOSS_PERCENT / 100)
        target = last_price * (1 + TARGET_PERCENT / 100)
        return {
            "ticker": ticker,
            "signal": signal,
            "last_price": round(last_price, 2),
            "ema20": round(ema20, 2),
            "stoploss": round(stoploss, 2),
            "target": round(target, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    else:
        return None  # Ignore SELL signals

# === FUNCTION: send email ===
def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.send_message(msg)

# === FUNCTION: log to Google Sheets ===
def log_to_sheet(signal):
    row = [
        signal["timestamp"],
        signal["ticker"],
        signal["last_price"],
        signal["ema20"],
        signal["stoploss"],
        signal["target"],
        ""  # Status (Hit/Miss) to fill later manually or via formula
    ]
    sheet.append_row(row)

# === MAIN ===
if __name__ == "__main__":
    signals = []
    for ticker in TICKERS:
        s = get_signal(ticker)
        if s:
            signals.append(s)
            log_to_sheet(s)

    if signals:
        email_body = f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for s in signals:
            email_body += (
                f"🪙 Ticker: {s['ticker']}\n"
                f"💰 Buy Price: ₹{s['last_price']}\n"
                f"📈 EMA20: ₹{s['ema20']}\n"
                f"⚠️ Stoploss: ₹{s['stoploss']}\n"
                f"🏁 Target Price: ₹{s['target']}\n"
                "---------------------------\n"
            )
        subject = f"Swing Trade Signals ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        send_email(subject, email_body)
        print("✅ Email sent!")
    else:
        print("No BUY signals at this time.")
