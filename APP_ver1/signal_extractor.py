import pandas as pd
from indicators import add_sma, add_rsi, add_macd, add_bollinger_bands

def _extract_custom_dates(df, mask_date, occurrences, base_filters):
    """
    【カスタム】アクション（クロス→押し目→回復）のシーケンスを解析し、
    最終的に条件が成立した（シグナルが点灯した）日付のリストを返します。
    """
    if not occurrences or df.empty:
        return []

    # MAのパラメータを取得
    fast_p = base_filters.get('global_ma_short', 5)
    slow_p = base_filters.get('global_ma_mid', 25)
    fast_col = f"SMA_{fast_p}"
    slow_col = f"SMA_{slow_p}"

    if fast_col not in df.columns: df = add_sma(df, fast_p)
    if slow_col not in df.columns: df = add_sma(df, slow_p)

    signal_dates = []

    # --- [ステップ0] ベースとなるクロスの発生日をすべて特定 ---
    base_occ = occurrences[0]
    cross_type = base_occ.get('cross_type', 'ゴールデンクロス')
    
    if "ゴールデン" in cross_type:
        base_mask = (df[fast_col].shift(1) <= df[slow_col].shift(1)) & (df[fast_col] > df[slow_col])
    else:
        base_mask = (df[fast_col].shift(1) >= df[slow_col].shift(1)) & (df[fast_col] < df[slow_col])

    base_dates = df[base_mask].index

    # 押し目や回復条件がない場合は、クロスした日をそのまま返す
    if len(occurrences) == 1:
        valid_dates = df[base_mask & mask_date].index
        return sorted(list(set(valid_dates)))

    when = occurrences[1]
    use_pullback = when.get('use_pullback', False)
    use_recovery = when.get('use_recovery', False)

    # --- [ステップ1・2] クロス日を起点に、その後の展開を追跡 ---
    for b_date in base_dates:
        current_idx = b_date
        is_valid_signal = True
        cross_price = df.loc[b_date, 'Close']

        # クロス発生から指定日数分の未来データ
        future_df = df.loc[b_date:].iloc[1 : when.get('check_days', 30) + 1]
        if future_df.empty:
            continue

        # [ステップ1] 押し目の検証
        if use_pullback:
            min_o = when.get('min_o_pct', 3.0) / 100.0
            max_o = when.get('max_o_pct', 8.0) / 100.0
            move_dir = when.get('o_direction', "下落(押し目)")

            passed_pb = False
            for row in future_df.itertuples():
                if "下落" in move_dir:
                    if row.Low < cross_price * (1.0 - max_o): break 
                    if row.Low <= cross_price * (1.0 - min_o):
                        current_idx = row.Index; passed_pb = True; break
                else: 
                    if row.High > cross_price * (1.0 + max_o): break
                    if row.High >= cross_price * (1.0 + min_o):
                        current_idx = row.Index; passed_pb = True; break
                        
            if not passed_pb:
                is_valid_signal = False

        # [ステップ2] トレンド回復の検証
        if is_valid_signal and use_recovery:
            rec_days = when.get('recovery_days', 10)
            recovery_df = df.loc[current_idx:].iloc[1 : rec_days + 1]
            passed_rec = False

            if ("ゴールデン" in cross_type and df.loc[current_idx, 'Close'] > df.loc[current_idx, fast_col]) or \
               ("デッド" in cross_type and df.loc[current_idx, 'Close'] < df.loc[current_idx, fast_col]):
                passed_rec = True
            else:
                for row in recovery_df.itertuples():
                    if ("ゴールデン" in cross_type and row.Close > getattr(row, fast_col)) or \
                       ("デッド" in cross_type and row.Close < getattr(row, fast_col)):
                        current_idx = row.Index; passed_rec = True; break
                        
            if not passed_rec:
                is_valid_signal = False

        # --- [ステップ3] 最終的なシグナル日の登録 ---
        if is_valid_signal:
            # 最終的な日付（回復した日）が、検証期間（mask_date）に含まれているかチェック
            if current_idx in mask_date.index and mask_date.loc[current_idx]:
                signal_dates.append(current_idx)

    return sorted(list(set(signal_dates)))


def extract_signal_dates(df, mask_date, action_triggers, base_filters):
    """
    アクションブロックのリストを評価し、シグナルが確定した日付（インデックス）のリストを返します。
    """
    if not action_triggers or df.empty:
        return []
        
    signal_dates_set = set()
    
    for idx, cond in enumerate(action_triggers):
        current_cond_dates = set()
        
        if cond['type'] == "ゴールデンクロス（SMA）":
            s_p, l_p = cond['params']['short'], cond['params']['long']
            if f"SMA_{s_p}" not in df.columns: df = add_sma(df, s_p)
            if f"SMA_{l_p}" not in df.columns: df = add_sma(df, l_p)
            mask = (df[f"SMA_{s_p}"].shift(1) <= df[f"SMA_{l_p}"].shift(1)) & (df[f"SMA_{s_p}"] > df[f"SMA_{l_p}"])
            current_cond_dates = set(df[mask & mask_date].index)
            
        elif cond['type'] == "株価のSMA上抜け":
            period = cond['params']['period']
            if f"SMA_{period}" not in df.columns: df = add_sma(df, period)
            mask = (df['Close'].shift(1) <= df[f"SMA_{period}"].shift(1)) & (df['Close'] > df[f"SMA_{period}"])
            current_cond_dates = set(df[mask & mask_date].index)
            
        elif cond['type'] == "RSI（指定値以下で反発）":
            r_p, r_t = cond['params']['period'], cond['params']['threshold']
            if f"RSI_{r_p}" not in df.columns: df = add_rsi(df, r_p)
            mask = (df[f"RSI_{r_p}"].shift(1) <= r_t) & (df[f"RSI_{r_p}"] > r_t)
            current_cond_dates = set(df[mask & mask_date].index)
            
        elif cond['type'] == "MACD（ゼロライン浮上）":
            if "MACD" not in df.columns: df = add_macd(df)
            mask = (df['MACD'].shift(1) <= 0) & (df['MACD'] > 0)
            current_cond_dates = set(df[mask & mask_date].index)
            
        elif cond['type'] == "ボリンジャーバンド（-2σタッチ）":
            period = cond['params']['period']
            if f"BB_Lower_{period}" not in df.columns: df = add_bollinger_bands(df, period)
            mask = df['Low'] <= df[f'BB_Lower_{period}']
            current_cond_dates = set(df[mask & mask_date].index)
            
        elif cond['type'] == "【カスタム】":
            # ★新規作成した専用関数で、波形を完全再現して日付を抽出
            dates = _extract_custom_dates(df, mask_date, cond.get('occurrences', []), base_filters)
            current_cond_dates = set(dates)

        # --- 論理結合 (AND / OR) による絞り込み ---
        if idx == 0:
            signal_dates_set = current_cond_dates
        else:
            if "AND" in cond['operator']:
                signal_dates_set = signal_dates_set.intersection(current_cond_dates)
            elif "OR" in cond['operator']:
                signal_dates_set = signal_dates_set.union(current_cond_dates)
                
    return sorted(list(signal_dates_set))