import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as datetime_time

st.set_page_config(page_title="MATRIX BO ENGINE", page_icon="⚡", layout="centered")
st.title("⚡ MATRIX HACKER EDITION")
st.subheader("~ Professional BO Signal Engine ~")
st.markdown("---")

st.sidebar.header("⚙️ SYSTEM SETTINGS")
ticker = st.sidebar.text_input("通貨ペア", value="USDJPY=X")
bb_p = st.sidebar.slider("ボリバン期間", min_value=5, max_value=50, value=20)
rsi_period = st.sidebar.slider("RSI期間", min_value=5, max_value=30, value=14)

if st.button("▶ RUN BACKTEST (システム起動)"):
    with st.spinner("MARKET DATA DOWNLOADING..."):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
        df_raw = yf.download(ticker, start=start_date, end=end_date, interval="1m", group_by="column")
        df = df_raw.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty:
            st.error("データの取得に失敗しました。")
        else:
            df['BB_Mid'] = df['Close'].rolling(window=bb_p).mean()
            df['BB_Std'] = df['Close'].rolling(window=bb_p).std()
            df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
            df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            df['Signal'] = 0
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC').tz_convert('Asia/Tokyo')
            
            cond_rsi_high = df['RSI'] >= 70
            cond_rsi_low = df['RSI'] <= 30
            cond_bb_lower = df['Close'] <= df['BB_Lower']
            cond_bb_upper = df['Close'] >= df['BB_Upper']
            cond_time = (df.index.time >= datetime_time(9, 0)) & (df.index.time <= datetime_time(23, 0))
            
            df.loc[cond_rsi_low & cond_bb_lower & cond_time, 'Signal'] = 1
            df.loc[cond_rsi_high & cond_bb_upper & cond_time, 'Signal'] = -1
            
            judge_minutes, payout_rate, entry_amount = 5, 1.85, 1000
            df['Judge_Price'] = df['Close'].shift(-judge_minutes)
            df['Win'] = 0
            df.loc[(df['Signal'] == 1) & (df['Judge_Price'] > df['Close']), 'Win'] = 1
            df.loc[(df['Signal'] == -1) & (df['Judge_Price'] < df['Close']), 'Win'] = 1
            
            df['Profit'] = 0
            df.loc[df['Win'] == 1, 'Profit'] = entry_amount * payout_rate - entry_amount
            df.loc[(df['Signal'] != 0) & (df['Win'] == 0), 'Profit'] = -entry_amount
            
            df_clean = df.dropna(subset=['Judge_Price'])
            trades = df_clean[df_clean['Signal'] != 0]
            num_trades = len(trades)
            
            st.success("ANALYSIS COMPLETE")
            if num_trades < 1:
                st.warning("サインが出ませんでした。")
            else:
                num_wins = trades['Win'].sum()
                win_rate = (num_wins / num_trades) * 100
                total_profit = trades['Profit'].sum()
                col1, col2, col3 = st.columns(3)
                col1.metric("総トレード数", f"{num_trades} 回")
                col2.metric("勝率", f"{win_rate:.2f} %")
                col3.metric("総損益", f"{total_profit:,} 円")
