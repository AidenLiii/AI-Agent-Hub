import os
import yfinance as yf
import google.generativeai as genai
import smtplib
import pandas as pd
import numpy as np
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Configuration & Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

def get_dca_signals(tickers):
    summary = []
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        # 增加获取数据的时间范围以确保 SMA200 计算准确
        hist = stock.history(period="2y") 
        
        if hist.empty or len(hist) < 200:
            print(f"Warning: {ticker} data is insufficient.")
            continue
            
        current_price = hist['Close'].iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # RSI 健壮性改进 (Wilder's Smoothing approximation)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        # 避免除以零
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs.fillna(100))) # 如果 loss 为 0，RSI 趋近 100
        current_rsi = rsi.iloc[-1]
        
        # 估值百分位（更适合定投参考）
        price_2y_low = hist['Close'].min()
        price_2y_high = hist['Close'].max()
        percentile = (current_price - price_2y_low) / (price_2y_high - price_2y_low) * 100
        
        summary.append(
            f"{ticker}: Price ${current_price:.2f}, "
            f"vs 200MA: {((current_price/sma_200)-1)*100:+.2f}%, "
            f"RSI: {current_rsi:.1f}, 2Y-Range: {percentile:.1f}%"
        )
    return "\n".join(summary)

def generate_report(raw_data):
    if not raw_data:
        return "No data available."
        
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = f"""
    Role: Senior Portfolio Manager (DCA Specialist).
    Task: Provide a Tactical DCA Advice Report.
    Input Data: {raw_data}

    DCA Logic:
    Aggressive Buy: RSI < 35 AND Price < 200MA.
    Standard DCA: RSI 35-70.
    Caution/Hold: RSI > 75 OR Price > 200MA + 20%.

    Requirements:
    1. Identify High Value Zones.
    2. Mixed Chinese and English. Use English for technical terms like 'Oversold', 'Mean Reversion'.
    3. No corporate fluff, just analysis.
    """
    response = model.generate_content(prompt)
    return response.text

def send_email(content):
    if not EMAIL_SENDER or not EMAIL_RECEIVER:
        print("Email configuration missing.")
        return
        
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = "Daily AI Stock Analysis Report"
    msg.attach(MIMEText(content, 'plain'))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    # 修正后缀: 513310.SS
    target_tickers = ["513310.SS", "NVDA", "TSLA"]
    
    print("Fetching stock data...")
    data = get_dca_signals(target_tickers)
    
    print("Generating AI report...")
    report = generate_report(data)
    
    print("Sending email...")
    send_email(report)
    print("Task completed successfully.")