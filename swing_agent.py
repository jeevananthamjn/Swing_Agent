import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIG ===
TICKERS = ["GOLDBEES.NS", "NIFTYBEES.NS", "ITBEES.NS", "GOLDPETAL.NS"]
EMAIL_FROM = "jeevanantham1989@gmail.com"
EMAIL_TO = "jeevanantham1989@gmail.com"
APP_PASSWORD = "gkbn qakv xrqy ygiw"
STOPLOSS_PERCENT = 1.5
TARGET_PERCENT = 3.0

# Google Sheets config
GSHEET_NAME = "SwingSignals"
CREDENTIALS_FILE = "credentials/swingagent-e6b363ab0671.json"

# === GOOGLE SHEETS SETUP ===
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GSHEET_NAME).sheet1  # First sheet

# === FUNCTION: get swing signal ===
def get_signal(ticker):
    data = yf.download(ticker, period="1mo", interval="1h")
    if data.empty:
        return None
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    last_row = data.iloc[-1]
    last_price = float(last_row["Close"])
    ema20 = float(last_row["EMA20"])

    # BUY signal only
    if last_price > ema20:
        stoploss = last_price * (1 - STOPLOSS_PERCENT / 100)
        target = last_price * (1 + TARGET_PERCENT / 100)
        return {
            "ticker": ticker,
            "signal": "BUY",
            "last_price": round(last_price, 2),
            "ema20": round(ema20, 2),
            "stoploss": round(stoploss, 2),
            "target": round(target, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    else:
        return None

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
        ""  # Status (Hit/Miss) to fill manually or later
    ]
    sheet.append_row(row)

# === FUNCTION: calculate weekly metrics ===
def weekly_summary():
    records = sheet.get_all_records()
    one_week_ago = datetime.now() - timedelta(days=7)
    weekly_signals = [r for r in records if datetime.strptime(r['Date'], "%Y-%m-%d %H:%M") >= one_week_ago]

    if not weekly_signals:
        return "No trades in the past week."

    total_signals = len(weekly_signals)
    wins = [r for r in weekly_signals if r.get("Status (Hit/Miss)", "").lower() == "win"]
    total_wins = len(wins)
    avg_gain = round(sum([(r['Target'] - r['Buy Price']) for r in weekly_signals]) / total_signals, 2)
    best = max(weekly_signals, key=lambda x: x['Target'] - x['Buy Price'])
    worst = min(weekly_signals, key=lambda x: x['Target'] - x['Buy Price'])

    summary = (
        f"📅 Weekly Swing Trade Summary ({(one_week_ago).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')})\n"
        f"Total Signals: {total_signals}\n"
        f"Total Wins: {total_wins}\n"
        f"Average Target Gain: ₹{avg_gain}\n"
        f"Best Ticker: {best['Ticker']} (Target - Buy: ₹{best['Target'] - best['Buy Price']:.2f})\n"
        f"Worst Ticker: {worst['Ticker']} (Target - Buy: ₹{worst['Target'] - worst['Buy Price']:.2f})\n"
    )
    return summary

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
        send_email(f"Swing Trade Signals ({datetime.now().strftime('%Y-%m-%d %H:%M')})", email_body)
        print("✅ Email sent!")

    # Send weekly summary if today is Monday 10:00 AM (example)
    if datetime.now().weekday() == 0 and datetime.now().hour == 10:
        summary = weekly_summary()
        send_email("📊 Weekly Swing Trade Summary", summary)
        print("✅ Weekly summary sent!")
    else:
        print("No weekly summary today.")
