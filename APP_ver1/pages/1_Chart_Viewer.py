import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import sys

# data_fetcher や indicators を読み込めるように親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_fetcher import fetch_stock_data
from indicators import add_sma

st.set_page_config(page_title="Chart Viewer", layout="wide")

# セッションにターゲット銘柄がない場合（直接このページを開いた場合）の処理
if 'target_ticker' not in st.session_state:
    st.warning("銘柄が選択されていません。メインページからスクリーニングを実行し、銘柄を選択してください。")
    if st.button("🏠 メインページに戻る"):
        st.switch_page("app.py")
    st.stop()

ticker = st.session_state['target_ticker']
start_date = st.session_state['target_start']
end_date = st.session_state['target_end']
global_ma = st.session_state.get('global_ma', {"short": 5, "mid": 25, "long": 75})

st.title(f"📈 詳細チャート分析: {ticker}")

if st.button("🔙 スクリーニング結果に戻る"):
    st.switch_page("app.py")

with st.spinner('データを取得中...'):
    # データを少し長めに取得（MA計算のため）
    import datetime
    buffer_start = pd.to_datetime(start_date) - datetime.timedelta(days=200)
    df = fetch_stock_data(ticker)
    
    if not df.empty:
        df = df.loc[buffer_start.strftime('%Y-%m-%d'):].copy()
        
        # 移動平均の追加
        df = add_sma(df, global_ma['short'])
        df = add_sma(df, global_ma['mid'])
        df = add_sma(df, global_ma['long'])
        
        # 表示期間でスライス
        mask = (df.index.strftime('%Y-%m-%d') >= str(start_date)) & (df.index.strftime('%Y-%m-%d') <= str(end_date))
        df_plot = df.loc[mask]
        
        if not df_plot.empty:
            # --- Plotlyによる美しいローソク足チャートの描画 ---
            fig = go.Figure()

            # ローソク足
            fig.add_trace(go.Candlestick(
                x=df_plot.index,
                open=df_plot['Open'], high=df_plot['High'],
                low=df_plot['Low'], close=df_plot['Close'],
                name='ローソク足',
                increasing_line_color='red', decreasing_line_color='green' # 日本式（陽線=赤、陰線=緑）
            ))

            # 移動平均線
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[f"SMA_{global_ma['short']}"], mode='lines', name=f"短期MA({global_ma['short']}日)", line=dict(color='blue', width=1)))
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[f"SMA_{global_ma['mid']}"], mode='lines', name=f"中期MA({global_ma['mid']}日)", line=dict(color='orange', width=1.5)))
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[f"SMA_{global_ma['long']}"], mode='lines', name=f"長期MA({global_ma['long']}日)", line=dict(color='purple', width=2)))

            # レイアウト調整
            fig.update_layout(
                title=f"{ticker} の値動き",
                yaxis_title='株価',
                xaxis_rangeslider_visible=False, # 下部の不要なスライダーを消す
                height=600,
                template="plotly_white"
            )

            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("※チャート上でマウスを動かすと詳細な価格が表示されます。ドラッグで拡大も可能です。")
        else:
            st.error("指定された期間のデータがありません。")