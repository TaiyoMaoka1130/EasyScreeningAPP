import streamlit as st
import pandas as pd
import datetime
import sys
import os
import plotly.graph_objects as go

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_fetcher import fetch_stock_data
from indicators import add_sma
from signal_extractor import extract_signal_dates
from backtest_engine import run_backtest_simulation
from backtest_evaluator import calculate_metrics

st.set_page_config(page_title="Backtest Dashboard", layout="wide", page_icon="🧪")

# =========================================================
# 0. セッションとデータの確認
# =========================================================
if 'selected_stocks' not in st.session_state or not st.session_state['selected_stocks']:
    st.warning("対象の銘柄がありません。メインページで銘柄を選択してください。")
    if st.button("🏠 メインページに戻る"):
        st.switch_page("app.py")
    st.stop()

selected_data = pd.DataFrame(st.session_state['selected_stocks'])
global_ma = st.session_state.get('global_ma', {"short": 5, "mid": 25, "long": 75})

# バックテスト専用の条件リストを初期化
if "buy_conditions" not in st.session_state:
    st.session_state.buy_conditions = []
if "sell_conditions" not in st.session_state:
    st.session_state.sell_conditions = []

# =========================================================
# 1. バックテスト設定 UI
# =========================================================
st.title("🧪 バックテスト・シミュレーター")
st.markdown("選定された銘柄に対して、指定した売買ルールで運用した場合の成績を検証します。")

with st.expander("⚙️ 1. 検証期間と環境設定", expanded=True):
    col_s, col_e = st.columns(2)
    with col_s: test_start = st.date_input("検証開始日", st.session_state.get('target_start', datetime.date(2026, 1, 1)))
    with col_e: test_end = st.date_input("検証終了日", st.session_state.get('target_end', datetime.date.today()))

with st.expander("📈 2. 買いシグナルの設定", expanded=True):
    st.caption("ここで設定した条件を満たした**翌日の始値**で買いエントリーします。")
    # ※メイン画面から条件をインポートするボタン
    if st.button("📥 メイン画面の検索条件を「買いシグナル」にコピーする"):
        if 'conditions' in st.session_state and st.session_state.conditions:
            import copy
            st.session_state.buy_conditions = copy.deepcopy(st.session_state.conditions)
            st.success("条件をコピーしました！")
            
    # 簡易表示（実際は ui_components を流用して編集可能に拡張できます）
    # === ここから差し替え ===
    if len(st.session_state.buy_conditions) > 0:
        for i, cond in enumerate(st.session_state.buy_conditions):
            # カスタム条件の場合、Whenモジュールの設定UIを展開して編集可能にする
            if cond['type'] == '【カスタム】' and 'occurrences' in cond and len(cond['occurrences']) > 1:
                when = cond['occurrences'][1]
                st.markdown(f"**■ 条件 {i+1}: Whenモジュール（買いトリガー）の調整**")
                
                use_pullback = st.checkbox("押し目を狙う", value=when.get('use_pullback', False), key=f"pb_{i}")
                if use_pullback:
                    col_w1, col_w2 = st.columns(2)
                    with col_w1:
                        when['min_o_pct'] = st.number_input("最小下落率 (%)", value=float(when.get('min_o_pct', 3.0)), key=f"min_{i}")
                    with col_w2:
                        when['max_o_pct'] = st.number_input("最大下落率 (%)", value=float(when.get('max_o_pct', 8.0)), key=f"max_{i}")
                
                use_recovery = st.checkbox("トレンド回復を確認してエントリー", value=when.get('use_recovery', False), key=f"rec_{i}")
                if use_recovery:
                    when['recovery_days'] = st.number_input("回復確認の最大日数", value=int(when.get('recovery_days', 10)), key=f"recd_{i}")
                    
                # 変更された数値をバックテスト用のWhenモジュールに保存
                when['use_pullback'] = use_pullback
                when['use_recovery'] = use_recovery
                cond['occurrences'][1] = when
            else:
                # カスタム以外の標準指標の場合は簡易表示
                st.info(f"条件 {i+1}: {cond['type']}")
    else:
        st.warning("買い条件が設定されていません。上のボタンからコピーしてください。")
    
with st.expander("📉 3. 売りシグナル・エグジット設定", expanded=True):
    st.caption("ポジション保有中に以下のいずれかの条件を満たした場合、決済を行います。")
    
    # 1. 通常のテクニカル売りシグナル
    sell_type = st.selectbox("テクニカル売りシグナル（トレンド終了など）", ["使用しない", "株価のSMA下抜け", "デッドクロス（SMA）"])
    sell_cond = {"type": sell_type, "operator": None, "params": {}}
    sc1, sc2 = st.columns(2)
    if sell_type == "株価のSMA下抜け":
        with sc1: sell_cond['params']['period'] = st.number_input("基準SMA", 1, 200, 25, key="sell_sma")
    elif sell_type == "デッドクロス（SMA）":
        with sc1: sell_cond['params']['short'] = st.number_input("短期SMA", 1, 100, 5, key="sell_short")
        with sc2: sell_cond['params']['long'] = st.number_input("長期SMA", 10, 300, 25, key="sell_long")
    
    st.divider()
    st.markdown("**■ 価格追従型エグジット（利益最大化・リスク管理）**")
    
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        # トレイリングストップUIの追加
        use_trailing = st.checkbox("📈 トレイリングストップを有効化", value=True)
        if use_trailing:
            trailing_stop_pct = st.number_input("高値からの下落率 (%)", min_value=1.0, max_value=30.0, value=10.0, step=1.0)
            st.caption("※エントリー後の最高値から指定%下がったら利益確定（または損切り）します。")
        else:
            trailing_stop_pct = 0.0
            
    with col_ex2:
        # 絶対損切りライン
        use_stop = st.checkbox("🛑 絶対損切りラインを有効化", value=True)
        if use_stop:
            stop_loss_pct = st.number_input("エントリー価格からの下落率 (%)", min_value=1.0, max_value=50.0, value=5.0, step=1.0)
            st.caption("※トレイリングが機能する前の、初期の致命的な下落を防ぎます。")
        else:
            stop_loss_pct = 0.0

# === 注意：すぐ下の「シミュレーションの実行」ループ内の呼び出しも修正が必要です ===
# ...
            # 売りシグナルを使用しない場合は空配列にする処理を追加
            if sell_type == "使用しない":
                sell_dates = []
            else:
                sell_dates = extract_signal_dates(df, mask_date, [sell_cond], base_filters)
            
            # エンジンの実行（★引数に trailing_stop_pct を追加）
            trades = run_backtest_simulation(ticker, df.loc[str(test_start):str(test_end)], buy_dates, sell_dates, stop_loss_pct, trailing_stop_pct)
            all_trades.extend(trades)

# =========================================================
# 2. シミュレーションの実行
# =========================================================
st.divider()
if st.button("🚀 バックテストを実行する", type="primary", use_container_width=True):
    if len(st.session_state.buy_conditions) == 0:
        st.error("買いシグナルを設定してください。")
        st.stop()
        
    progress_bar = st.progress(0)
    status_text = st.empty()
    all_trades = []
    
    tickers = selected_data['コード'].astype(str).tolist()
    total = len(tickers)
    
    # 仮想の売りシグナルリストを作成
    current_sell_conditions = [sell_cond]
    base_filters = {"global_ma_short": global_ma['short'], "global_ma_mid": global_ma['mid'], "global_ma_long": global_ma['long']}
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"シミュレーション中... {ticker} ({i+1}/{total})")
        
        # ★追加：selected_data からこの ticker の企業名を取得
        stock_name = selected_data[selected_data['コード'].astype(str) == ticker]['企業名'].iloc[0]
        
        df = fetch_stock_data(ticker)
        
        if not df.empty:
            # MAの事前計算
            df = add_sma(df, global_ma['short'])
            df = add_sma(df, global_ma['mid'])
            df = add_sma(df, global_ma['long'])
            
            mask_date = (df.index.strftime('%Y-%m-%d') >= str(test_start)) & (df.index.strftime('%Y-%m-%d') <= str(test_end))
            
            # シグナルの抽出
            buy_dates = extract_signal_dates(df, mask_date, st.session_state.buy_conditions, base_filters)
            
            if sell_type == "使用しない":
                sell_dates = []
            else:
                sell_dates = extract_signal_dates(df, mask_date, [sell_cond], base_filters)
            
            # エンジンの実行（★ row['企業名'] ではなく stock_name を渡す）
            trades = run_backtest_simulation(
                ticker, 
                stock_name, 
                df.loc[str(test_start):str(test_end)], 
                buy_dates, 
                sell_dates, 
                stop_loss_pct, 
                trailing_stop_pct
            )
            all_trades.extend(trades)
            
        progress_bar.progress((i + 1) / total)
        
    status_text.text("バックテスト完了！")
    
    # =========================================================
    # 3. 結果の評価とダッシュボード表示
    # =========================================================
    if len(all_trades) > 0:
        # (指標表示 m1〜m6 のコードはそのまま)
        
        st.markdown("### 📝 詳細なトレード履歴")
        df_trades = pd.DataFrame(all_trades)
        
        # ★ 1. ticker列を「銘柄コード : 銘柄名」に統合
        df_trades['銘柄'] = df_trades['ticker'].astype(str) + " : " + df_trades['name']
        
        # 表示用の順序整理
        df_display = df_trades[['銘柄', 'entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct', 'exit_reason']]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.divider()

        # ★ 2. 各銘柄ごとの成績・チャート・売買タイミングの表示
        st.markdown("### 🔍 個別銘柄の分析（成績とチャート）")
        
        # 履歴にあるユニークな銘柄ごとにダッシュボードを生成
        unique_tickers = df_trades['ticker'].unique()
        
        for t_code in unique_tickers:
            # この銘柄だけのトレード履歴を抽出
            t_trades = df_trades[df_trades['ticker'] == t_code]
            t_name = t_trades['name'].iloc[0]
            
            # この銘柄の合計リターンを計算して、タイトルでパッと見れるようにする
            total_return = round(t_trades['return_pct'].sum(), 2)
            emoji = "🔥" if total_return > 0 else "💧"
            
            # アコーディオン（Expander）のタイトルに合計成績を表示
            with st.expander(f"{emoji} {t_code} {t_name} | 合計損益: {total_return}% | トレード: {len(t_trades)}回", expanded=False):
                
                # --- ① 個別銘柄の成績表示 ---
                s_metrics = calculate_metrics(t_trades.to_dict('records'))
                if s_metrics:
                    sm1, sm2, sm3, sm4 = st.columns(4)
                    sm1.metric("勝率", f"{s_metrics['勝率']}%")
                    sm2.metric("期待値 (1回平均)", f"{s_metrics['期待値']}%", delta_color="normal" if s_metrics['期待値'] >= 0 else "inverse")
                    sm3.metric("平均利益", f"+{s_metrics['平均利益']}%")
                    sm4.metric("平均損失", f"{s_metrics['平均損失']}%")
                
                st.divider()

                # --- ② チャートと売買ポイントの可視化 ---
                df_chart = fetch_stock_data(t_code)
                if not df_chart.empty:
                    df_plot = df_chart.loc[str(test_start):str(test_end)].copy()
                    
                    fig = go.Figure()
                    # ローソク足
                    fig.add_trace(go.Candlestick(
                        x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                        low=df_plot['Low'], close=df_plot['Close'], name='株価',
                        increasing_line_color='red', decreasing_line_color='green'
                    ))
                    
                    # 買いポイントのプロット
                    fig.add_trace(go.Scatter(
                        x=t_trades['entry_date'], y=t_trades['entry_price'],
                        mode='markers', name='買いエントリー',
                        marker=dict(symbol='triangle-up', size=14, color='red', line=dict(width=2, color='white'))
                    ))
                    
                    # 売りポイントのプロット
                    fig.add_trace(go.Scatter(
                        x=t_trades['exit_date'], y=t_trades['exit_price'],
                        mode='markers', name='エグジット',
                        marker=dict(symbol='triangle-down', size=14, color='blue', line=dict(width=2, color='white')),
                        text=t_trades['exit_reason'] # ホバー時に理由を表示
                    ))
                    
                    fig.update_layout(
                        title=f"{t_name} の値動きと売買ポイント",
                        xaxis_rangeslider_visible=False,
                        height=500,
                        template="plotly_white",
                        hovermode="x unified",
                        margin=dict(t=40, b=10, l=10, r=10)
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"bt_chart_{t_code}")
                
                # --- ③ この銘柄専用の詳細トレード履歴 ---
                st.markdown("**▼ この銘柄のトレード詳細**")
                # 銘柄名などの重複情報を省き、スッキリした表にする
                t_display = t_trades[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct', 'exit_reason']].copy()
                st.dataframe(t_display, hide_index=True, use_container_width=True)