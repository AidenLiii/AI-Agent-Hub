import os
import yfinance as yf
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Configuration & Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

def get_stock_data(tickers):
    summary = []
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        if len(hist) < 2:
            continue
        close_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        change_pct = ((close_price - prev_close) / prev_close) * 100
        summary.append(f"{ticker}: Price ${close_price:.2f}, Change {change_pct:.2f}%")
    return "\n".join(summary)

def generate_report(raw_data):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash')
    
    prompt = f"""
    Role: Senior Investment Advisor.
    Input Data: {raw_data}
    Task: Provide a market analysis report in mixed Chinese and English.
    Requirements: 
    * Include Market Sentiment and Trend Analysis.
    * Provide clear Action Items.
    * Keep it concise.
    """
    response = model.generate_content(prompt)
    return response.text

def send_email(content):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = "Daily AI Stock Analysis Report"
    
    msg.attach(MIMEText(content, 'plain'))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    # Target Stocks
    target_tickers = ["AAPL", "NVDA", "TSLA"]
    
    # Execution Flow
    print("Fetching stock data...")
    data = get_stock_data(target_tickers)
    
    print("Generating AI report...")
    report = generate_report(data)
    
    print("Sending email...")
    send_email(report)
    print("Task completed successfully.")