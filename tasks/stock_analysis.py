import os
import yfinance as yf
import google.generativeai as genai
import smtplib
import pandas as pd
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
        # 获取基础信息
        info = stock.info
        hist = stock.history(period="2y") # 获取2年数据计算分位数
        
        current_price = hist['Close'].iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # 计算 RSI (简化版)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # 估值数据
        pe_ratio = info.get('trailingPE', 'N/A')
        
        summary.append(
            f"{ticker}: Price ${current_price:.2f}, "
            f"vs 200MA: {((current_price/sma_200)-1)*100:+.2f}%, "
            f"RSI: {rsi:.1f}, PE: {pe_ratio}"
        )
    return "\n".join(summary)

def generate_report(raw_data):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = f"""
    Role: Senior Portfolio Manager (DCA Specialist).
    Task: Provide a Tactical DCA Advice Report.
    Input Data: {raw_data} (Including RSI, 200MA distance, and PE).

    DCA Logic:
    Aggressive Buy (加仓): If RSI < 35 and Price < 200MA. This is a Value Opportunity.
    Standard DCA (常规持有): If RSI between 35-70. Keep the plan unchanged.
    Caution/Hold (暂缓加仓): If RSI > 75 or Price > 200MA by 20%. This indicates Overextended status. High risk of short-term reversal.

    Requirements:
    Identify which tickers are in the High Value Zone for adding positions.
    Explain the Cost Basis impact of the current price.
    Keep it concise in mixed Chinese and English. Avoid generic advice.
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
    target_tickers = ["513310.sh", "NVDA", "TSLA"]
    
    # Execution Flow
    print("Fetching stock data...")
    data = get_dca_signals(target_tickers)
    
    print("Generating AI report...")
    report = generate_report(data)
    
    print("Sending email...")
    send_email(report)
    print("Task completed successfully.")