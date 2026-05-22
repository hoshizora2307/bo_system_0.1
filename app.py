import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as datetime_time

# ページの設定（マトリックス風の黒・緑を基調にするための設定）
st.set_page_config(page_title="MATRIX BO ENGINE", page_icon="⚡", layout="centered")

# カスタムCSSでマトリックス風のデザインを適用
st.markdown("""
    <style>
    .stApp { background-color: black; color: #00FF41; }
    h1, h2, h3, p, span, label { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; }
    .stButton>button { background-color: #003311; color: #00FF41; border: 1px solid #00FF41; width: 100%; }
    .stButton>button:hover { background-color: #00FF41; color: black; }
    div[data-testid="stMetricValue"] { color: #00FF41 !important; }
    div[data-testid="stMetricLabel"] { color: #00FF41 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ MATRIX HACKER EDITION")
st.subheader("~ Professional BO Signal Engine ~")

st.markdown("---")

# ユーザーが設定を選ぶサイドバー
st.sidebar.header("⚙️ SYSTEM SETTINGS")
ticker = st.sidebar.text_input("通貨ペア (Yahoo Finance表記)", value="USDJPY=X")
bb_p = st.sidebar.slider("ボランジャーバンド期間", min_value=5, max_value=50, value=20)
rsi_period = st.sidebar.slider("RSI期間", min_value=5, max_value=30, value=14)

# アプリ上の起動ボタン
if st.button("▶ RUN BACKTEST (システム起動)"):
    with st.spinner("MARKET DATA DOWNLOADING..."):
        # 【修正ポイント】直近7日間の1分足を安定して取得する指定に変更
        df_raw = yf.download(ticker, period="7d", interval="1m", group_by="column")
        df = df_raw.copy()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty:
            st.error("データの取得に失敗しました。時間をおいて試すか、設定を確認してください。")
        else:
            # テクニカル計算
            df['BB_Mid'] = df['Close'].rolling(window=bb_p).mean()
            df['BB_Std'] = df['Close'].rolling(window=bb_p).std()
            df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
            df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # サイン判定
            df['Signal'] = 0
            cond_rsi_high = df['RSI'] >= 70
            cond_rsi_low = df['RSI'] <= 30
            cond_bb_lower = df['Close'] <= df['BB_Lower']
            cond_bb_upper = df['Close'] >= df['BB_Upper']
            
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC').tz_convert('Asia/Tokyo')
            
            cond_time = (df.index.time >= datetime_time(9, 0)) & (df.index.time <= datetime_time(23, 0))
            
            df.loc[cond_rsi_low & cond_bb_lower & cond_time, 'Signal'] = 1
            df.loc[cond_rsi_high & cond_bb_upper & cond_time, 'Signal'] = -1
            
            # 勝敗判定
            judge_minutes = 5
            payout_rate = 1.85
            entry_amount = 1000
            df['Judge_Price'] = df['Close'].shift(-judge_minutes)
            df['Win'] = 0
            
            df.loc[(df['Signal'] == 1) & (df['Judge_Price'] > df['Close']), 'Win'] = 1
            df.loc[(df['Signal'] != 0) & (df['Win'] == 0), 'Profit'] = -entry_amount
            df.loc[(df['Signal'] == -1) & (df['Judge_Price'] < df['Close']), 'Win'] = 1
            
            df['Profit'] = 0
            df.loc[df['Win'] == 1, 'Profit'] = entry_amount * payout_rate - entry_amount
            df.loc[(df['Signal'] != 0) & (df['Win'] == 0), 'Profit'] = -entry_amount
            
            df_clean = df.dropna(subset=['Judge_Price'])
            trades = df_clean[df_clean['Signal'] != 0]
            num_trades = len(trades)
            
            # 結果表示
            st.success("ANALYSIS COMPLETE (解析完了)")
            
            if num_trades < 1:
                st.warning("条件に一致するトレードが発生しませんでした。")
            else:
                num_wins = trades['Win'].sum()
                num_losses = num_trades - num_wins
                win_rate = (num_wins / num_trades) * 100
                total_profit = trades['Profit'].sum()
                
                # 画面に見やすくカード型で表示
                col1, col2, col3 = st.columns(3)
                col1.metric("総トレード数", f"{num_trades} 回")
                col2.metric("勝率", f"{win_rate:.2f} %")
                col3.metric("総損益", f"{total_profit:,} 円")
                
                st.markdown("### 詳細レポート")
                st.text(f"・勝ち数 : {num_wins} 回 / 負け数 : {num_losses} 回")
