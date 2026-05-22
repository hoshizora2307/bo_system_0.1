import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, time as datetime_time
import time

# ページの設定
st.set_page_config(page_title="PRO TRADER QUANT MONITOR", page_icon="📈", layout="centered")

# カスタムCSS：TradingView風の洗練された漆黒モダンUIへ
st.markdown("""
    <style>
    .stApp {
        background-color: #131722;
        color: #d1d4dc;
    }
    h1, h2, h3, p, span, label, div {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
    h1 {
        font-weight: 700 !important;
        color: #ffffff !important;
        letter-spacing: -0.02em;
    }
    section[data-testid="stSidebar"] {
        background-color: #1c2030 !important;
        border-right: 1px solid #2a2e3f;
    }
    .stButton>button {
        background: linear-gradient(90deg, #2962ff 0%, #1e40af 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(41, 98, 255, 0.3);
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(41, 98, 255, 0.5);
    }
    div[data-testid="stMetric"] {
        background-color: #1c2030;
        border: 1px solid #2a2e3f;
        border-radius: 8px;
        padding: 12px 18px !important;
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #787b86 !important;
        font-size: 0.8rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# アラート音再生関数
def play_alert_sound():
    sound_html = """
    <audio autoplay>
        <source src="https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg" type="audio/ogg">
    </audio>
    """
    st.components.v1.html(sound_html, height=0, width=0)

# メインヘッダー
st.title("📈 PRO TRADER QUANT MONITOR")
st.markdown("<p style='color: #787b86; margin-top: -15px;'>Advanced Binary Options Signal Engine // Powered by TradingView Style</p>", unsafe_allow_html=True)
st.markdown("<div style='border-bottom: 1px solid #2a2e3f; margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# サイドバー設定
st.sidebar.markdown("<h2 style='color: #fff; font-size: 1.1rem; margin-bottom: 15px;'>⚙️ CONFIGURATION</h2>", unsafe_allow_html=True)
ticker = st.sidebar.text_input("通貨ペア", value="USDJPY=X")
bb_p = st.sidebar.slider("ボリンジャーバンド期間", min_value=5, max_value=50, value=20)
rsi_period = st.sidebar.slider("RSI期間", min_value=5, max_value=30, value=14)

st.write("⏱️ 起動すると1分ごとに自動リフレッシュされ、ローソク足チャートとシグナルがリアルタイムに更新されます。")

if st.button("▶ LAUNCH LIVE MONITOR"):
    status_area = st.empty()
    metric_area = st.empty()
    alert_area = st.empty()
    chart_area = st.empty()
    
    while True:
        current_time_str = datetime.now().strftime("%H:%M:%S")
        status_area.markdown(f"<p style='color: #2962ff; font-weight: 600; display: flex; align-items: center;'><span style='height: 8px; width: 8px; background-color: #2962ff; border-radius: 50%; display: inline-block; margin-right: 8px;'></span> LIVE // SCANNING IN PROGRESS // JST: {current_time_str}</p>", unsafe_allow_html=True)
        
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
            
            latest_row = df.iloc[-1]
            latest_price = latest_row['Close']
            latest_rsi = latest_row['RSI']
            latest_sig = latest_row['Signal']
            
            # メトリクスボード表示
            with metric_area.container():
                c1, c2, c3 = st.columns(3)
                c1.metric("RATE", f"{latest_price:.3f}")
                c2.metric("RSI (14)", f"{latest_rsi:.1f}")
                with c3:
                    if latest_sig == 1:
                        st.markdown("<div style='background-color: #0e3626; border: 1px solid #26a69a; border-radius:6px; padding: 10px; text-align:center; color:#26a69a; font-weight:700; margin-top:2px;'>UP ARROW HIGH</div>", unsafe_allow_html=True)
                    elif latest_sig == -1:
                        st.markdown("<div style='background-color: #401924; border: 1px solid #ef5350; border-radius:6px; padding: 10px; text-align:center; color:#ef5350; font-weight:700; margin-top:2px;'>DOWN ARROW LOW</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='background-color: #1e222d; border: 1px solid #2a2e3f; border-radius:6px; padding: 10px; text-align:center; color:#787b86; font-weight:600; margin-top:2px;'>SCANNING...</div>", unsafe_allow_html=True)
            
            # 音アラート検知
            recent_df = df.tail(5)
            if (recent_df['Signal'] != 0).any() or latest_rsi >= 68 or latest_rsi <= 32:
                with alert_area:
                    st.markdown("<div style='background: #1e222d; color: #2962ff; border: 1px solid #2962ff; padding: 12px; border-radius: 6px; font-weight:600; margin-bottom:15px;'>⚡ SIGNAL ALERT: チャンス接近中</div>", unsafe_allow_html=True)
                    play_alert_sound()
            else:
                alert_area.empty()
                
            # --- 4. TradingView風 メインローソク足＆RSIサブチャート（2段構成） ---
            df_plot = df.tail(60)
            
            # 2行1列のサブプロットを作成（ローソク足の行を広く、RSIの行を狭く）
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.06, 
                                row_width=[0.3, 0.7]) # 下段(RSI)が30%, 上段(価格)が70%
            
            # 【上段】本格ローソク足チャートの追加
            fig.add_trace(go.Candlestick(
                x=df_plot.index,
                open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'],
                name='Price',
                increasing_line_color='#26a69a', increasing_fillcolor='#26a69a', # 陽線：エメラルド
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'  # 陰線：ローズ
            ), row=1, col=1)
            
            # ボリバン上限・下限（TradingViewのように主張しすぎない細い青破線）
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_Upper'], name='BB Upper', line=dict(color='rgba(41, 98, 255, 0.4)', width=1.5, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_Mid'], name='BB Mid', line=dict(color='rgba(255, 152, 0, 0.6)', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_Lower'], name='BB Lower', line=dict(color='rgba(41, 98, 255, 0.4)', width=1.5, dash='dash')), row=1, col=1)
            
            # HIGHサインの矢印プロット（ローソク足の下に上向き▲）
            high_signals = df_plot[df_plot['Signal'] == 1]
            fig.add_trace(go.Scatter(
                x=high_signals.index, y=high_signals['Low'] - (high_signals['High'] - high_signals['Low'])*0.5,
                mode='markers+text', name='UP ARROW HIGH', text=['UP ARROW<br>HIGH']*len(high_signals), textposition='bottom center',
                marker=dict(symbol='triangle-up', size=14, color='#00e676'),
                textfont=dict(color='#00e676', size=10)
            ), row=1, col=1)
            
            # LOWサインの矢印プロット（ローソク足の上に下向き▼）
            low_signals = df_plot[df_plot['Signal'] == -1]
            fig.add_trace(go.Scatter(
                x=low_signals.index, y=low_signals['High'] + (low_signals['High'] - low_signals['Low'])*0.5,
                mode='markers+text', name='DOWN ARROW LOW', text=['DOWN ARROW<br>LOW']*len(low_signals), textposition='top center',
                marker=dict(symbol='triangle-down', size=14, color='#ff1744'),
                textfont=dict(color='#ff1744', size=10)
            ), row=1, col=1)
            
            # 【下段】RSIインジケーターチャートの追加
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI (14)', line=dict(color='#9c27b0', width=1.5)), row=2, col=1)
            
            # RSIの境界線（70：赤ライン、30：青ライン）
            fig.add_shape(type="line", x0=df_plot.index[0], y0=70, x1=df_plot.index[-1], y1=70, line=dict(color="#ef5350", width=1.5), row=2, col=1)
            fig.add_shape(type="line", x0=df_plot.index[0], y0=30, x1=df_plot.index[-1], y1=30, line=dict(color="#2962ff", width=1.5), row=2, col=1)
            # 50の中央点線
            fig.add_shape(type="line", x0=df_plot.index[0], y0=50, x1=df_plot.index[-1], y1=50, line=dict(color="rgba(120, 123, 134, 0.3)", width=1, dash="dash"), row=2, col=1)
            
            # レイアウト調整（背景色、グリッド、右側スケール）
            fig.update_layout(
                paper_bgcolor='#131722', plot_bgcolor='#131722',
                xaxis=dict(gridcolor='#2a2e3f', rangeslider_visible=False, showticklabels=False),
                xaxis2=dict(gridcolor='#2a2e3f', tickfont=dict(color='#787b86')),
                yaxis=dict(gridcolor='#2a2e3f', side='right', tickfont=dict(color='#787b86')),
                yaxis2=dict(gridcolor='#2a2e3f', side='right', range=[0, 100], tickfont=dict(color='#787b86')),
                legend=dict(font=dict(color='#d1d4dc'), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=10, b=10),
                height=550
            )
            
            chart_area.plotly_chart(fig, use_container_width=True)
            
        else:
            status_area.error("MARKET DATA CONNECTING...")
            
        time.sleep(60)
