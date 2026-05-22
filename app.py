import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, time as datetime_time
import time

# ページの設定（横幅をスマートに使うためレイアウトを微調整）
st.set_page_config(page_title="NEO QUANT SYSTEM", page_icon="⚡", layout="centered")

# カスタムCSS：野暮ったさを徹底排除し、引き締まったダークコックピットを構築
st.markdown("""
    <style>
    /* 全体を重厚感のある漆黒（ダークチャコール）に */
    .stApp {
        background-color: #090a0f;
        color: #e2e8f0;
    }
    /* フォントを無機質で知的なデザインに統一 */
    h1, h2, h3, p, span, label, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important;
    }
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.03em;
        color: #ffffff !important;
    }
    /* サイドバーの背景と境界線をシャープに */
    section[data-testid="stSidebar"] {
        background-color: #11131c !important;
        border-right: 1px solid #1e2235;
    }
    /* 起動ボタン：フラットで未来的なインディゴブルー。無駄な丸みを排除 */
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.7rem 1.5rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em;
        box-shadow: 0 4px 15px rgba(29, 78, 216, 0.3);
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(29, 78, 216, 0.5);
    }
    /* メトリクス（情報パネル）：枠線を薄くし、背景に溶け込ませる */
    div[data-testid="stMetric"] {
        background-color: #11131c;
        border: 1px solid #1e2235;
        border-radius: 8px;
        padding: 12px 16px !important;
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-size: 0.8rem !important;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    </style>
    """, unsafe_allow_html=True)

# アラート音再生関数
def play_alert_sound():
    sound_html = """
    <audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg" type="audio/ogg"></audio>
    """
    st.components.v1.html(sound_html, height=0, width=0)

# メインヘッダー
st.title("⚡ NEO QUANT SYSTEM")
st.markdown("<p style='color: #64748b; margin-top: -15px;'>次世代型アルゴリズム監視モニター // 1分足リアルタイム自動更新</p>", unsafe_allow_html=True)
st.markdown("<div style='border-bottom: 1px solid #1e2235; margin-bottom: 25px;'></div>", unsafe_allow_html=True)

# サイドバー設定
st.sidebar.markdown("<h2 style='color: #fff; font-size: 1.1rem; margin-bottom: 15px;'>⚙️ RISK SYSTEM</h2>", unsafe_allow_html=True)
ticker = st.sidebar.text_input("通貨ペア", value="USDJPY=X")
atr_period = st.sidebar.slider("ATRボラティリティ期間", min_value=5, max_value=30, value=14)
consecutive_candles = st.sidebar.slider("連続同方向足カウント", min_value=2, max_value=7, value=4)

st.write("⏱️ モニターを起動すると自動ループに入り、1分ごとに無駄のない高精度チャートが更新されます。")

if st.button("▶ システム監視を開始する"):
    status_area = st.empty()
    metric_area = st.empty()
    alert_area = st.empty()
    chart_area = st.empty()
    
    while True:
        current_time_str = datetime.now().strftime("%H:%M:%S")
        status_area.markdown(f"<p style='color: #3b82f6; font-weight: 700; display: flex; align-items: center;'><span style='height: 8px; width: 8px; background-color: #3b82f6; border-radius: 50%; display: inline-block; margin-right: 8px;'></span> リアルタイム監視中 // 最新同期: {current_time_str}</p>", unsafe_allow_html=True)
        
        # 1. データの取り込み
        df_raw = yf.download(ticker, period="3d", interval="1m", group_by="column", progress=False)
        df = df_raw.copy()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if not df.empty:
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC').tz_convert('Asia/Tokyo')

            # 2. 次世代フィルターロジック計算
            # ATR (True Range) 
            high_low = df['High'] - df['Low']
            high_cp = np.abs(df['High'] - df['Close'].shift())
            low_cp = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(window=atr_period).mean()
            df['ATR_MA'] = df['ATR'].rolling(window=20).mean()
            
            # ショック・プライス（急激な大荒れ）の検知
            df['Body_Size'] = np.abs(df['Close'] - df['Open'])
            df['Shock_Threshold'] = df['ATR'] * 1.8
            
            # ローソク足方向
            df['Direction'] = np.where(df['Close'] > df['Open'], 1, np.where(df['Close'] < df['Open'], -1, 0))
            
            # 3. シグナル生成
            df['Signal'] = 0
            for i in range(len(df)):
                if i < 20:
                    continue
                
                # 連続同方向足の確認
                sub_series = df['Direction'].iloc[i-consecutive_candles+1 : i+1]
                is_all_up = (sub_series == 1).all()
                is_all_down = (sub_series == -1).all()
                
                # 急騰・急落
                is_shock_up = df['Close'].iloc[i] > df['Open'].iloc[i] and df['Body_Size'].iloc[i] > df['Shock_Threshold'].iloc[i]
                is_shock_down = df['Close'].iloc[i] < df['Open'].iloc[i] and df['Body_Size'].iloc[i] > df['Shock_Threshold'].iloc[i]
                
                # 適正ボラティリティ判定
                is_proper_volatility = df['ATR'].iloc[i] > df['ATR_MA'].iloc[i] * 0.5 and df['ATR'].iloc[i] < df['ATR_MA'].iloc[i] * 2.5
                
                current_pixel_time = df.index[i].time()
                is_market_time = datetime_time(9, 0) <= current_pixel_time <= datetime_time(23, 0)
                
                if is_market_time and is_proper_volatility:
                    if is_all_up or is_shock_up:
                        df.iloc[i, df.columns.get_loc('Signal')] = -1 # LOW
                    elif is_all_down or is_shock_down:
                        df.iloc[i, df.columns.get_loc('Signal')] = 1  # HIGH

            latest_row = df.iloc[-1]
            latest_price = latest_row['Close']
            latest_atr = latest_row['ATR']
            latest_sig = latest_row['Signal']
            
            # 情報ボードの更新
            with metric_area.container():
                c1, c2, c3 = st.columns(3)
                c1.metric("現在価格", f"{latest_price:.3f}")
                c2.metric("市場エネルギー (ATR)", f"{latest_atr:.4f}")
                with c3:
                    if latest_sig == 1:
                        st.markdown("<div style='background-color: #07271e; border: 1px solid #10b981; border-radius:6px; padding: 10px; text-align:center; color:#10b981; font-weight:700; font-size:0.85rem; margin-top:2px;'>⚡ HIGH検出</div>", unsafe_allow_html=True)
                    elif latest_sig == -1:
                        st.markdown("<div style='background-color: #3b0d17; border: 1px solid #f43f5e; border-radius:6px; padding: 10px; text-align:center; color:#f43f5e; font-weight:700; font-size:0.85rem; margin-top:2px;'>⚡ LOW検出</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='background-color: #11131c; border: 1px solid #1e2235; border-radius:6px; padding: 10px; text-align:center; color:#64748b; font-weight:600; font-size:0.85rem; margin-top:2px;'>⏳ チャンス待機中</div>", unsafe_allow_html=True)
            
            # シグナル点灯時の音アラート
            if latest_sig != 0:
                with alert_area:
                    st.markdown("<div style='background: #11131c; color: #3b82f6; border: 1px solid #3b82f6; padding: 12px; border-radius: 6px; font-weight:600; margin-bottom:15px; font-size:0.85rem;'>🚨 アルゴリズムが優位性を検知。エントリータイミング。</div>", unsafe_allow_html=True)
                    play_alert_sound()
            else:
                alert_area.empty()
                
            # --- 4. 無駄を削ぎ落とした2段式・機能美チャート（直近50分） ---
            df_plot = df.tail(50)
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.04, 
                                row_width=[0.25, 0.75])
            
            # 【上段】ローソク足チャート
            fig.add_trace(go.Candlestick(
                x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'],
                name='価格', Chelsea_color=True,
                increasing_line_color='#10b981', increasing_fillcolor='#10b981', # 陽線：無機質なエメラルド
                decreasing_line_color='#f43f5e', decreasing_fillcolor='#f43f5e'  # 陰線：シャープなレッド
            ), row=1, col=1)
            
            # HIGHサイン（無駄な文字を省き、洗練された▲マークに統合）
            high_signals = df_plot[df_plot['Signal'] == 1]
            fig.add_trace(go.Scatter(
                x=high_signals.index, y=high_signals['Low'] - (high_signals['High'] - high_signals['Low'])*0.3,
                mode='markers+text', name='HIGHサイン', text=['▲ HIGH']*len(high_signals), textposition='bottom center',
                marker=dict(symbol='triangle-up', size=14, color='#10b981', line=dict(color='#ffffff', width=1)),
                textfont=dict(color='#10b981', size=11, font=dict(family='Arial Black'))
            ), row=1, col=1)
            
            # LOWサイン（洗練された▼マーク）
            low_signals = df_plot[df_plot['Signal'] == -1]
            fig.add_trace(go.Scatter(
                x=low_signals.index, y=low_signals['High'] + (low_signals['High'] - low_signals['Low'])*0.3,
                mode='markers+text', name='LOWサイン', text=['▼ LOW']*len(low_signals), textposition='top center',
                marker=dict(symbol='triangle-down', size=14, color='#f43f5e', line=dict(color='#ffffff', width=1)),
                textfont=dict(color='#f43f5e', size=11, font=dict(family='Arial Black'))
            ), row=1, col=1)
            
            # 【下段】ATRボラティリティ（余計な背景色を塗らず、スマートな一本のラインに）
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['ATR'], name='ATR (市場エネルギー)', line=dict(color='#3b82f6', width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['ATR_MA'], name='ATR基準線', line=dict(color='rgba(100, 116, 139, 0.4)', width=1.5, dash='dot')), row=2, col=1)
            
            # チャート全体を部屋の照明を落としても眩しくない洗練された「トーン」に調整
            fig.update_layout(
                paper_bgcolor='#08090c', plot_bgcolor='#08090c',
                xaxis=dict(gridcolor='#161923', rangeslider_visible=False, showticklabels=False),
                xaxis2=dict(gridcolor='#161923', tickfont=dict(color='#64748b')),
                yaxis=dict(gridcolor='#161923', side='right', tickfont=dict(color='#64748b')),
                yaxis2=dict(gridcolor='#161923', side='right', tickfont=dict(color='#64748b')),
                legend=dict(font=dict(color='#94a3b8'), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=10, b=10), height=520
            )
            
            chart_area.plotly_chart(fig, use_container_width=True)
            
        else:
            status_area.error("データノードに接続中...")
            
        time.sleep(60)
