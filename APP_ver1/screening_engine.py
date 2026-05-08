import pandas as pd
import numpy as np
import datetime
import concurrent.futures # ★新規追加（並列処理用ライブラリ）
from data_fetcher import fetch_stock_data, fetch_fundamental_data
from indicators import add_sma, add_rsi, add_macd, add_bollinger_bands

# ★新しく切り出したカスタムロジックを読み込む
from custom_logic import check_custom_sequence

# =========================================================
# 【新規分離】1銘柄分の処理を行う独立関数（並列化のため）
# ※ ここに元々の run_screening の中身がそっくり移動しています
# =========================================================
def _process_single_ticker(ticker, start_date, end_date, base_filters, action_triggers):
    try:
        # --- 【第0層】ファンダメンタルズ足切り ---
        if any([base_filters.get(k) for k in ['use_per_filter', 'use_pbr_filter', 'use_roe_filter', 'use_div_filter', 'use_mcap_filter']]):
            f_data = fetch_fundamental_data(ticker)
            
            def check_bounds(val, min_val, max_val):
                if val is None: return False
                if min_val is not None and val < min_val: return False
                if max_val is not None and val > max_val: return False
                return True

            if base_filters.get('use_per_filter') and not check_bounds(f_data.get('per'), base_filters.get('min_per'), base_filters.get('max_per')):
                return None # ※並列処理では continue の代わりに return None を使います
            if base_filters.get('use_pbr_filter') and not check_bounds(f_data.get('pbr'), base_filters.get('min_pbr'), base_filters.get('max_pbr')):
                return None
            if base_filters.get('use_roe_filter') and not check_bounds(f_data.get('roe'), base_filters.get('min_roe'), base_filters.get('max_roe')):
                return None
            if base_filters.get('use_div_filter') and not check_bounds(f_data.get('div_yield'), base_filters.get('min_div'), base_filters.get('max_div')):
                return None
            if base_filters.get('use_mcap_filter') and not check_bounds(f_data.get('market_cap'), base_filters.get('min_mcap'), base_filters.get('max_mcap')):
                return None

        # --- 株価履歴の取得 ---
        raw_df = fetch_stock_data(ticker)
        if raw_df.empty or len(raw_df) < 50: 
            return None
        
        # 【バグ修正】タイムゾーンエラーの回避と、200日線の担保
        # トレンドフィルター（200日線）も考慮した上で最大のバッファ日数を算出
        max_ma = max(base_filters.get('global_ma_short', 5), 
                     base_filters.get('global_ma_mid', 25), 
                     base_filters.get('global_ma_long', 75), 
                     200) # ← 200を確保
        buffer_days = int(max_ma * 1.5) + 10 
        
        buffer_start_date = pd.to_datetime(start_date) - datetime.timedelta(days=buffer_days)
        # ▼ 日付を「文字列（YYYY-MM-DD）」に変換してからスライスすることで、時差エラーを完全に防ぐ
        buffer_start_str = buffer_start_date.strftime('%Y-%m-%d')
        df = raw_df.loc[buffer_start_str:].copy()
        
        if df.empty:
            return None

        # 全体で共通して使う3本のMAを計算
        df = add_sma(df, base_filters['global_ma_short'])
        df = add_sma(df, base_filters['global_ma_mid'])
        df = add_sma(df, base_filters['global_ma_long'])
        
        # 最終的な検証期間のマスクを作成
        mask_date = (df.index.strftime('%Y-%m-%d') >= str(start_date)) & (df.index.strftime('%Y-%m-%d') <= str(end_date))
        df_period = df.loc[mask_date]
        
        if df_period.empty:
            return None
            
        # =========================================================
        # 【第1層】ベース環境フィルターの拡充
        # =========================================================
        passed_layer1 = True
        if base_filters.get('use_period_growth', False):
            start_price = df_period.iloc[0]['Open']
            end_price = df_period.iloc[-1]['Close']
            if start_price > 0:
                growth_pct = ((end_price - start_price) / start_price) * 100
                min_g, max_g = base_filters.get('min_growth_pct'), base_filters.get('max_growth_pct')
                if min_g is not None and growth_pct < min_g: passed_layer1 = False
                if max_g is not None and growth_pct > max_g: passed_layer1 = False
                    
        if base_filters.get('use_close_filter', False):
            latest_close = df.iloc[-1]['Close']
            min_c, max_c = base_filters.get('min_close_price'), base_filters.get('max_close_price')
            if min_c is not None and latest_close < min_c: passed_layer1 = False
            if max_c is not None and latest_close > max_c: passed_layer1 = False

        if base_filters.get('use_volume_filter', False):
            avg_volume = df_period['Volume'].mean()
            min_v, max_v = base_filters.get('min_volume'), base_filters.get('max_volume')
            if min_v is not None and avg_volume < min_v: passed_layer1 = False
            if max_v is not None and avg_volume > max_v: passed_layer1 = False
            
        if base_filters.get('use_trend_filter', False):
            if "SMA_200" not in df.columns: df = add_sma(df, 200)
            if df_period.iloc[-1]['Close'] < df_period.iloc[-1]['SMA_200']: passed_layer1 = False

        if not passed_layer1:
            return None

        # --- 【第1.5層・第2層・第3層】アクションと検証 ---
        if len(action_triggers) == 0:
            stock_passed = True
        else:
            for cond in action_triggers:
                if cond['type'] == "ゴールデンクロス（SMA）":
                    s_p, l_p = cond['params']['short'], cond['params']['long']
                    if f"SMA_{s_p}" not in df.columns: df = add_sma(df, s_p)
                    if f"SMA_{l_p}" not in df.columns: df = add_sma(df, l_p)
                elif cond['type'] == "株価のSMA上抜け":
                    period = cond['params']['period']
                    if f"SMA_{period}" not in df.columns: df = add_sma(df, period)
                elif cond['type'] == "RSI（指定値以下で反発）":
                    r_p = cond['params']['period']
                    if f"RSI_{r_p}" not in df.columns: df = add_rsi(df, r_p)
                elif cond['type'] == "MACD（ゼロライン浮上）":
                    if "MACD" not in df.columns: df = add_macd(df)
                elif cond['type'] == "ボリンジャーバンド（-2σタッチ）":
                    period = cond['params']['period']
                    if f"BB_Lower_{period}" not in df.columns: df = add_bollinger_bands(df, period)
            
            stock_passed = False 
            for idx, cond in enumerate(action_triggers):
                cond_passed = False
                
                # 🔴 【第1.5層】カスタム・シーケンスの処理
                if cond['type'] == "【カスタム】":
                    cond_passed = check_custom_sequence(df, mask_date, cond.get('occurrences', []), base_filters)
                
                # 🔵 【第2・3層】既存のアクションの処理
                else:
                    if cond['type'] == "ゴールデンクロス（SMA）":
                        s_p, l_p = cond['params']['short'], cond['params']['long']
                        full_mask = (df[f"SMA_{s_p}"].shift(1) <= df[f"SMA_{l_p}"].shift(1)) & (df[f"SMA_{s_p}"] > df[f"SMA_{l_p}"])
                    elif cond['type'] == "株価のSMA上抜け":
                        period = cond['params']['period']
                        full_mask = (df['Close'].shift(1) <= df[f"SMA_{period}"].shift(1)) & (df['Close'] > df[f"SMA_{period}"])
                    elif cond['type'] == "RSI（指定値以下で反発）":
                        r_p, r_t = cond['params']['period'], cond['params']['threshold']
                        full_mask = (df[f"RSI_{r_p}"].shift(1) <= r_t) & (df[f"RSI_{r_p}"] > r_t)
                    elif cond['type'] == "MACD（ゼロライン浮上）":
                        full_mask = (df['MACD'].shift(1) <= 0) & (df['MACD'] > 0)
                    elif cond['type'] == "ボリンジャーバンド（-2σタッチ）":
                        period = cond['params']['period']
                        full_mask = df['Low'] <= df[f'BB_Lower_{period}']
                    
                    signal_days = df[full_mask & mask_date]
                    req_occ = cond['advanced']['min_occ'] if cond['advanced']['use_occ'] else 1
                    
                    if len(signal_days) >= req_occ:
                        if cond['advanced']['use_perf']:
                            target_ratio = 1.0 + (cond['advanced']['target_pct'] / 100.0)
                            stop_pct = cond['advanced'].get('stop_loss_pct', 0.0) if cond['advanced'].get('use_stop_loss', False) else 0.0
                            stop_ratio = 1.0 - (stop_pct / 100.0)
                            
                            success_count = 0
                            for signal_date, row in signal_days.iterrows():
                                future_df = df.loc[signal_date:].iloc[1:cond['advanced']['check_days']+1]
                                if not future_df.empty:
                                    hit_target = False
                                    for _, f_row in future_df.iterrows():
                                        if stop_pct > 0 and f_row['Low'] <= row['Close'] * stop_ratio: break
                                        if f_row['High'] >= row['Close'] * target_ratio: hit_target = True; break
                                    if hit_target: success_count += 1
                            if success_count > 0: cond_passed = True
                        else:
                            cond_passed = True
                        
                if idx == 0: stock_passed = cond_passed
                else:
                    if "AND" in cond['operator']: stock_passed = stock_passed and cond_passed
                    elif "OR" in cond['operator']: stock_passed = stock_passed or cond_passed
                    
        if stock_passed:
            f_data = fetch_fundamental_data(ticker) if base_filters.get('use_per_filter', False) else {"per": None}
            # ※並列処理では、結果を辞書として直接 return します
            return {
                "銘柄コード": ticker,
                "最新終値": df.iloc[-1]['Close'],
                "PER": f_data.get("per")
            }
            
    except Exception:
        pass
    
    return None

# =========================================================
# メインのスクリーニング実行エンジン
# ※ ここは並列処理の「指示出し」だけを行うスッキリした形になります
# =========================================================
def run_screening(tickers, start_date, end_date, base_filters, action_triggers, progress_callback=None):
    matched_results = []
    total_tickers = len(tickers)
    processed_count = 0
    
    # ★ max_workers=10 で10銘柄を同時に計算します
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 全銘柄のタスクを投げる
        futures = {executor.submit(_process_single_ticker, t, start_date, end_date, base_filters, action_triggers): t for t in tickers}
        
        # 計算が終わったものから順次受け取ってリストに追加する
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                matched_results.append(result)
            
            # プログレスバーの更新
            processed_count += 1
            if progress_callback:
                progress_callback(processed_count, total_tickers)
                
    return matched_results