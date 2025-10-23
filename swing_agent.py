import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==============================
# Configuration via GitHub Secrets
# ==============================
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_TO = os.environ.get("EMAIL_TO")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
GSHEET_JSON = os.environ.get("GSHEET_JSON")
GSHEET_NAME = "SwingSignals"  # Name of your Google Sheet
TICKERS = ["GOLDBEES.NS","ITBEES.NS","NIFTYBEES.NS"]  # Add your tickers
EMA_PERIOD = 20
STOPLOSS_PERCENT = 1.0  # 1%
TARGET_PERCENT = 3.0    # 3%

# ==============================
# Google Sheet Setup
# ==============================
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GSHEET_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(GSHEET_NAME).sheet1

# Ensure headers exist
if sheet.row_count < 1:
    sheet.append_row(["Date","Ticker","Buy Price","EMA20","Stoploss","Target","Status"])

# ==============================
# Functions
# ==============================
def get_data(ticker):
    try:
        data = yf.download(ticker, period="1mo", interval="1h", auto_adjust=True)
        if data.empty:
            print(f"No data for {ticker}")
            return None
        data["EMA20"] = data["Close"].ewm(span=EMA_PERIOD, adjust=False).mean()
        return data
    except Exception as e:
        print(f"Error downloading {ticker}: {e}")
        return None

def generate_signal(data):
    last_row = data.iloc[-1]
    last_close = float(last_row["Close"])
    ema20 = float(last_row["EMA20"])
    if last_close > ema20:
        signal = "BUY"
        stoploss = round(last_close * (1 - STOPLOSS_PERCENT/100), 2)
        target = round(last_close * (1 + TARGET_PERCENT/100), 2)
        return signal, last_close, ema20, stoploss, target
    return None, None, None, None, None

def log_to_sheet(date, ticker, buy_price, ema20, stoploss, target, status="Open"):
    sheet.append_row([date, ticker, buy_price, ema20, stoploss, target, status])

def send_email(subject, body):
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, APP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print("Email sent successfully")
    except Exception as e:
        print("Email failed:", e)

# ==============================
# Main Script
# ==============================
email_body = ""
for ticker in TICKERS:
    data = get_data(ticker)
    if data is None:
        continue
    signal, buy_price, ema20, stoploss, target = generate_signal(data)
    if signal == "BUY":
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_to_sheet(date_str, ticker, buy_price, ema20, stoploss, target)
        email_body += (
            f"📅 Date: {date_str}\n"
            f"🪙 Ticker: {ticker}\n"
            f"💰 Last Price: ₹{buy_price}\n"
            f"📈 EMA20: ₹{ema20}\n"
            f"🛑 Stoploss: ₹{stoploss}\n"
            f"🎯 Target: ₹{target}\n\n"
        )

if email_body:
    subject = f"Swing Trade Signals ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    send_email(subject, email_body)
    print("Signals processed and email sent.")
else:
    print("No BUY signals today.")

# ==============================
# Weekly Summary (Optional)
# ==============================
def weekly_summary():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return
    one_week_ago = datetime.now() - timedelta(days=7)
    df["Date"] = pd.to_datetime(df["Date"])
    last_week = df[df["Date"] >= one_week_ago]
    if last_week.empty:
        return

    total_signals = len(last_week)
    wins = len(last_week[last_week["Status"]=="Hit"])
    avg_gain = round(last_week["Target"].mean() - last_week["Buy Price"].mean(),2)
    best_ticker = last_week.loc[(last_week["Target"]-last_week["Buy Price"]).idxmax()]["Ticker"]
    worst_ticker = last_week.loc[(last_week["Target"]-last_week["Buy Price"]).idxmin()]["Ticker"]

    summary = (
        f"📊 Weekly Summary (Last 7 Days)\n"
        f"Total Signals: {total_signals}\n"
        f"Wins: {wins}\n"
        f"Avg Gain: ₹{avg_gain}\n"
        f"Best Ticker: {best_ticker}\n"
        f"Worst Ticker: {worst_ticker}\n"
    )
    send_email(f"Weekly Swing Trade Summary ({datetime.now().strftime('%Y-%m-%d')})", summary)
    print("Weekly summary sent.")

# Uncomment below to send summary every Monday
# if datetime.now().weekday() == 0:
#     weekly_summary()
