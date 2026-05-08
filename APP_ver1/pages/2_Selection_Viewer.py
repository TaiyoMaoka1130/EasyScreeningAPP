import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import sys
import datetime

# ルートディレクトリのモジュールを読み込めるようにパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_fetcher import fetch_stock_data
from indicators import add_sma

st.set_page_config(page_title="Selected Analysis", layout="wide", page_icon="🎯")

# セッションチェック
if 'selected_stocks' not in st.session_state or not st.session_state['selected_stocks']:
    st.warning("銘柄が選択されていません。メインページからスクリーニングを行い、銘柄を選択してください。")
    if st.button("🏠 メインページに戻る"):
        st.switch_page("app.py")
    st.stop()

selected_data = pd.DataFrame(st.session_state['selected_stocks'])
start_date = st.session_state['target_start']
end_date = st.session_state['target_end']
global_ma = st.session_state.get('global_ma', {"short": 5, "mid": 25, "long": 75})

st.title("🎯 選定銘柄の比較分析")

col_nav1, col_nav2 = st.columns([1, 4])
with col_nav1:
    if st.button("🔙 検索結果に戻る", use_container_width=True):
        st.switch_page("app.py")

# --- 1. 選定銘柄サマリー表 ---
st.subheader("📋 選定銘柄リスト")
st.dataframe(selected_data.drop(columns=['選択']), hide_index=True, use_container_width=True)

st.divider()

# --- 2. 連続チャート分析 ---
st.subheader("📈 詳細チャート・ビュー")
st.caption("選定された銘柄のチャートを順番に表示します。")

for _, row in selected_data.iterrows():
    ticker = str(row['コード'])
    with st.expander(f"📊 {row['企業名']} ({ticker}) - 業種: {row['業種']}", expanded=True):
        # データの取得
        buffer_start = pd.to_datetime(start_date) - datetime.timedelta(days=200)
        df = fetch_stock_data(ticker)
        
        if not df.empty:
            df = df.loc[buffer_start.strftime('%Y-%m-%d'):].copy()
            df = add_sma(df, global_ma['short'])
            df = add_sma(df, global_ma['mid'])
            df = add_sma(df, global_ma['long'])
            
            mask = (df.index.strftime('%Y-%m-%d') >= str(start_date)) & (df.index.strftime('%Y-%m-%d') <= str(end_date))
            df_plot = df.loc[mask]
            
            if not df_plot.empty:
                fig = go.Figure()
                # ローソク足
                fig.add_trace(go.Candlestick(
                    x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                    low=df_plot['Low'], close=df_plot['Close'], name='価格'
                ))
                # 各移動平均線
                colors = ['#1f77b4', '#ff7f0e', '#9467bd']
                for j, m_type in enumerate(['short', 'mid', 'long']):
                    m_days = global_ma[m_type]
                    fig.add_trace(go.Scatter(
                        x=df_plot.index, y=df_plot[f"SMA_{m_days}"],
                        mode='lines', name=f"{m_days}日MA",
                        line=dict(width=1.5, color=colors[j])
                    ))
                
                fig.update_layout(
                    height=500, margin=dict(l=0, r=0, b=0, t=30),
                    xaxis_rangeslider_visible=False, template="plotly_white",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker}")
            else:
                st.info("この期間の株価データが取得できませんでした。")
        else:
            st.error(f"{ticker} のデータ取得に失敗しました。")