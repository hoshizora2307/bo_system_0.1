import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as datetime_time
import time

# ページの設定（高級感のあるダークモードにするためワイド表示＆タイトル設定）
st.set_page_config(page_title="PRO TRADER LIVE ENGINE", page_icon="📈", layout="centered")

# カスタムCSS：ダサい要素を徹底排除し、洗練された海外モダン風UIへ
st.markdown("""
    <style>
    /* 全体の背景を洗練された漆黒（チャコールブラック）に */
    .stApp {
        background-color: #0d0e11;
        color: #e2e8f0;
    }
    /* フォントをスマートなSans-Serif系に統一 */
    h1, h2, h3, p, span, label, div {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.05em;
        background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    /* サイドバーのデザイン調整 */
    section[data-testid="stSidebar"] {
        background-color: #161a22 !important;
        border-right: 1px solid #262b36;
    }
    /* ボタンを未来的なネオンブルーのミニマルデザインに */
    .stButton>button {
        background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
    }
    /* メトリクス（数字表示カード）の高級化 */
    div[data-testid="stMetric"] {
        background-color: #161a22;
        border: 1px solid #262b36;
        border-radius: 12px;
        padding: 15px 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        font-family: 'SF Pro Display', sans-serif !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    /* アラートメッセージの見た目調整 */
    .stAlert {
        border-radius: 12px !important;
        background-color: #1e1b4b !important;
        border: 1px solid #3730a3 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 音鳴らし用の音声埋め込み関数
def play_alert_sound():
    sound_html = """
    <audio autoplay>
        <source src="https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg" type="audio/ogg">
    </audio>
    """
    st.components.v1.html(sound_html, height=0, width=0)

# メインヘッダー
st.title("📈 QUANT LIVE MONITOR")
st.markdown("<p style='color: #64748b; margin-top: -15px;'>High-Performance Binary Options Analytics Platform</p>", unsafe_allow_html=True)
st.markdown("<div style='border-bottom: 1px solid #262b36; margin-bottom: 25px;'></div>", unsafe_allow_html=True)

# サイドバー設定
st.sidebar.markdown("<h2 style='color: #fff; font-size: 1.2rem; margin-bottom: 20px;'>⚙️ CONFIGURATION</h2>", unsafe_allow_html=True)
ticker = st.sidebar.text_input("通貨ペア", value="USDJPY=X")
bb_p = st.sidebar.slider("ボリンジャーバンド期間", min_value=5, max_value=50, value=20)
rsi_period = st.sidebar.slider("RSI期間", min_value=5, max_value=30, value=14)

st.write("⏱️ モニターを開始すると1分ごとに自動でデータを取得し、取引画面がリアルタイム更新されます。")

# モニター起動スイッチ
if st.button("▶ LAUNCH LIVE MONITOR"):
    status_area = st.empty()
    metric_area = st.empty()
    chart_area = st.empty()
    alert_area = st.empty()
    
    while True:
        current_time_str = datetime.now().strftime("%H:%M:%S")
        status_area.markdown(f"<p style='color: #38bdf8; font-weight: 600; display: flex; align-items: center;'><span style='height: 10px; width: 10px; background-color: #0ea5e9; border-radius: 50%; display: inline-block; margin-right: 8px; animate: pulse;'></span> LIVE STREAMING ENGINE // LAST UPDATE: {current_time_str}</p>", unsafe_allow_html=True)
        
        # 1. 最新データの取得
        df_raw = yf.download(ticker, period="2d", interval="1m", group_by="column", progress=False)
        df = df_raw.copy()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if not df.empty:
            # 2. テクニカル計算
            df['BB_Mid'] = df['Close'].rolling(window=bb_p).mean()
            df['BB_Std'] = df['Close'].rolling(window=bb_p).std()
            df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
            df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            # 3. シグナル判定
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
            
            # 直近の最新状態を取得
            latest_row = df.iloc[-1]
            latest_price = latest_row['Close']
            latest_rsi = latest_row['RSI']
            latest_sig = latest_row['Signal']
            
            # ボードのリアルタイム更新
            with metric_area.container():
                c1, c2, c3 = st.columns(3)
                c1.metric("RATE", f"{latest_price:.3f}")
                c2.metric("RSI (14)", f"{latest_rsi:.1f}")
                
                # シグナルステータスを美しく表示
                with c3:
                    if latest_sig == 1:
                        st.markdown("<div style='background-color: #064e3b; border: 1px solid #059669; border-radius:12px; padding: 12px; text-align:center; color:#10b981; font-weight:700; margin-top:3px;'>🔥 HIGH SIGNAL</div>", unsafe_allow_html=True)
                    elif latest_sig == -1:
                        st.markdown("<div style='background-color: #4c0519; border: 1px solid #dc2626; border-radius:12px; padding: 12px; text-align:center; color:#f43f5e; font-weight:700; margin-top:3px;'>🔥 LOW SIGNAL</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='background-color: #1e293b; border: 1px solid #475569; border-radius:12px; padding: 12px; text-align:center; color:#94a3b8; font-weight:600; margin-top:3px;'>⏳ SCANNING...</div>", unsafe_allow_html=True)
            
            # 4. 音アラート条件
            recent_df = df.tail(5)
            if (recent_df['Signal'] != 0).any() or latest_rsi >= 68 or latest_rsi <= 32:
                with alert_area:
                    st.markdown("<div style='background: linear-gradient(90deg, #4f46e5 0%, #3b82f6 100%); color: white; padding: 15px; border-radius: 12px; font-weight:600; margin-bottom:20px; box-shadow:0 10px 15px -3px rgba(59,130,246,0.3);'>⚡ ALERT: シグナル接近、または条件一致を検知！</div>", unsafe_allow_html=True)
                    play_alert_sound()
            else:
                alert_area.empty()
                
            # 5. TradingView風の洗練されたチャート描画（直近60分）
            df_plot = df.tail(60)
            fig = go.Figure()
            
            # メイン価格ライン（洗練された細身のライトブルー）
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'], mode='lines', name='Price', line=dict(color='#38bdf8', width=2.5)))
            
            # ボリバン（境界線を目立たせず、領域をうっすらハイテク風に塗る）
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_Upper'], name='BB Upper', line=dict(color='rgba(148, 163, 184, 0.15)', width=1, dash='dot')))
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_Lower'], name='BB Lower', line=dict(color='rgba(148, 163, 184, 0.15)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(38, 43, 54, 0.15)'))
            
            # HIGHサイン（ネオンエメラルドの上向き矢印 ▲）
            high_signals = df_plot[df_plot['Signal'] == 1]
            fig.add_trace(go.Scatter(x=high_signals.index, y=high_signals['Close'], mode='markers', name='Buy Signal',
                                     marker=dict(symbol='triangle-up', size=16, color='#10b981', line=dict(color='#fff', width=1.5))))
            
            # LOWサイン（ネオンローズの下向き矢印 ▼）
            low_signals = df_plot[df_plot['Signal'] == -1]
            fig.add_trace(go.Scatter(x=low_signals.index, y=low_signals['Close'], mode='markers', name='Sell Signal',
                                     marker=dict(symbol='triangle-down', size=16, color='#f43f5e', line=dict(color='#fff', width=1.5))))
            
            # チャート背景をダークネイビーグレー、格子線を極薄に
            fig.update_layout(
                paper_bgcolor='#0d0e11', plot_bgcolor='#0d0e11',
                xaxis=dict(gridcolor='#1e293b', title='', tickfont=dict(color='#64748b')),
                yaxis=dict(gridcolor='#1e293b', title='', side='right', tickfont=dict(color='#64748b')),
                legend=dict(font=dict(color='#94a3b8'), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=10, b=10),
                height=450
            )
            
            chart_area.plotly_chart(fig, use_container_width=True)
            
        else:
            status_area.error("MARKET DATA CONNECTING...")
            
        time.sleep(60)
