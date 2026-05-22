import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as px
from datetime import datetime, timedelta, time as datetime_time

# ページの設定
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

# サイドバー設定
st.sidebar.header("⚙️ SYSTEM SETTINGS")
ticker = st.sidebar.text_input("通貨ペア (Yahoo Finance表記)", value="USDJPY=X")
bb_p = st.sidebar.slider("ボランジャーバンド期間", min_value=5, max_value=50, value=20)
rsi_period = st.sidebar.slider("RSI期間", min_value=5, max_value=30, value=14)

if st.button("▶ RUN BACKTEST (システム起動)"):
    with st.spinner("MARKET DATA DOWNLOADING..."):
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
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            # サイン判定
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
            
            # 勝敗判定
            judge_minutes = 5
            payout_rate = 1.85
            entry_amount = 1000
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
            
            st.success("ANALYSIS COMPLETE (解析完了)")
            
            if num_trades < 1:
                st.warning("条件に一致するトレードが発生しませんでした。")
            else:
                num_wins = trades['Win'].sum()
                num_losses = num_trades - num_wins
                win_rate = (num_wins / num_trades) * 100
                total_profit = trades['Profit'].sum()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("総トレード数", f"{num_trades} 回")
                col2.metric("勝率", f"{win_rate:.2f} %")
                col3.metric("総損益", f"{total_profit:,} 円")
                
                # --- 【新規追加】インタラクティブ・シグナルチャートの描画 ---
                st.markdown("### 📊 SIGNAL CHART (直近データ)")
                
                # 直近200データ分に絞って見やすく描画
                df_plot = df.tail(200)
                
                fig = px.Figure()
                
                # 価格ライン（マトリックスグリーン）
                fig.add_trace(px.Scatter(x=df_plot.index, y=df_plot['Close'], name='Price', line=dict(color='#00FF41', width=2)))
                # ボリバン上限・下限（うっすら緑）
                fig.add_trace(px.Scatter(x=df_plot.index, y=df_plot['BB_Upper'], name='BB Upper', line=dict(color='rgba(0, 255, 65, 0.3)', dash='dash')))
                fig.add_trace(px.Scatter(x=df_plot.index, y=df_plot['BB_Lower'], name='BB Lower', line=dict(color='rgba(0, 255, 65, 0.3)', dash='dash')))
                
                # HIGHサイン（上向き矢印：水色）
                high_signals = df_plot[df_plot['Signal'] == 1]
                fig.add_trace(px.Scatter(x=high_signals.index, y=high_signals['Close'], mode='markers', name='HIGH (Buy)',
                                         marker=dict(symbol='triangle-up', size=14, color='#00FFFF', line=dict(width=2))))
                
                # LOWサイン（下向き矢印：ピンク）
                low_signals = df_plot[df_plot['Signal'] == -1]
                fig.add_trace(px.Scatter(x=low_signals.index, y=low_signals['Close'], mode='markers', name='LOW (Sell)',
                                         marker=dict(symbol='triangle-down', size=14, color='#FF00FF', line=dict(width=2))))
                
                # チャートの背景を黒に統一
                fig.update_layout(
                    paper_bgcolor='black', plot_bgcolor='black',
                    xaxis=dict(gridcolor='#113311', title='Time'), yaxis=dict(gridcolor='#113311', title='Price'),
                    legend=dict(font=dict(color='#00FF41')), margin=dict(l=10, r=10, t=10, b=10)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### 詳細レポート")
                st.text(f"・勝ち数 : {num_wins} 回 / 負け数 : {num_losses} 回")
