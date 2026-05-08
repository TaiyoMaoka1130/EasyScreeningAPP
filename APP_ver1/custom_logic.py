import pandas as pd

# =========================================================
# 【第1.5層】カスタム・シーケンス判定モジュール（完全統合版）
# =========================================================
def check_custom_sequence(df, mask_date, occurrences, base_filters):
    """
    ユーザーが選択した「When」と「Condition」を動的に解釈し、指定された回数(L回)を満たすか判定します。
    """
    if not occurrences:
        return True

    # 検証期間だけのデータ（高値更新の判定などに使用）
    df_period = df[mask_date]

    for occ in occurrences:
        l_required_cycles = occ.get('l_times', 1)
        
        for when in occ.get('whens', []):
            when_type = when.get('when_type', "スイング(山・谷)")
            
            # --- 1. 起点(When)の特定 ---
            trigger_points = [] 
            
            if when_type == "スイング(山・谷)":
                target = when.get('target_type', "底値")
                sw = when.get('swing_window', 5)
                w_size = sw * 2 + 1
                
                if target == "高値":
                    is_peak = df['High'] == df['High'].rolling(w_size, center=True).max()
                    for idx, row in df[is_peak & mask_date].iterrows(): 
                        trigger_points.append((idx, row['High']))
                else:
                    is_valley = df['Low'] == df['Low'].rolling(w_size, center=True).min()
                    for idx, row in df[is_valley & mask_date].iterrows(): 
                        trigger_points.append((idx, row['Low']))

            elif when_type == "MAクロス":
                cross_dir = when.get('cross_direction', "ゴールデンクロス")
                use_pullback = when.get('use_pullback', False)
                use_recovery = when.get('use_recovery', False)
                
                ma_cols = {
                    "短期MA": f"SMA_{base_filters['global_ma_short']}",
                    "中期MA": f"SMA_{base_filters['global_ma_mid']}",
                    "長期MA": f"SMA_{base_filters['global_ma_long']}"
                }
                fast_col = ma_cols[when.get('ma_fast', "短期MA")]
                slow_col = ma_cols[when.get('ma_slow', "中期MA")]
                
                sma_fast = df[fast_col]
                sma_slow = df[slow_col]
                
                if cross_dir == "ゴールデンクロス":
                    cross_mask = (sma_fast.shift(1) <= sma_slow.shift(1)) & (sma_fast > sma_slow)
                else:
                    cross_mask = (sma_fast.shift(1) >= sma_slow.shift(1)) & (sma_fast < sma_slow)
                
                for c_date in df[cross_mask & mask_date].index:
                    cross_price = df.loc[c_date, 'Close']
                    future_df = df.loc[c_date:]
                    current_idx = c_date
                    is_valid_signal = True
                    
                    # --- [ステップ1] 変動率レンジ（押し目）の検証 ---
                    if use_pullback:
                        min_o = when.get('min_o_pct', 3.0) / 100.0
                        max_o = when.get('max_o_pct', 8.0) / 100.0
                        move_dir = when.get('o_direction', "下落(押し目)")
                        
                        passed_pb = False
                        # ★ iterrows() を itertuples() に変更し、ドット(.)アクセスで爆速化
                        for row in future_df.itertuples():
                            if "下落" in move_dir:
                                if row.Low < cross_price * (1.0 - max_o): break 
                                if row.Low <= cross_price * (1.0 - min_o):
                                    current_idx = row.Index; passed_pb = True; break
                            else: 
                                if row.High > cross_price * (1.0 + max_o): break
                                if row.High >= cross_price * (1.0 + min_o):
                                    current_idx = row.Index; passed_pb = True; break
                        if not passed_pb: is_valid_signal = False
                        
                    # --- [ステップ2] トレンド回復の検証 ---
                    if is_valid_signal and use_recovery:
                        rec_days = when.get('recovery_days', 10)
                        recovery_df = df.loc[current_idx:].iloc[1 : rec_days + 1]
                        passed_rec = False
                        
                        if cross_dir == "ゴールデンクロス" and df.loc[current_idx, 'Close'] > df.loc[current_idx, fast_col]:
                            passed_rec = True
                        elif cross_dir == "デッドクロス" and df.loc[current_idx, 'Close'] < df.loc[current_idx, fast_col]:
                            passed_rec = True
                        else:
                            # ★ こちらも itertuples() に変更。動的な列名アクセスには getattr() を使用
                            for row in recovery_df.itertuples():
                                if (cross_dir == "ゴールデンクロス" and row.Close > getattr(row, fast_col)) or \
                                   (cross_dir == "デッドクロス" and row.Close < getattr(row, fast_col)):
                                    current_idx = row.Index; passed_rec = True; break
                        if not passed_rec: is_valid_signal = False
                        
                    if is_valid_signal:
                        trigger_points.append((current_idx, df.loc[current_idx, 'Close']))

            # --- 2. 条件(Condition)の評価 ---
            completed_cycles = 0
            for t_date, t_price in trigger_points:
                future_df = df.loc[t_date:].iloc[1:]
                if future_df.empty: continue
                
                conditions_passed = True
                for cnd in when.get('conditions', []):
                    cond_type = cnd.get('cond_type', "価格変動(N%到達)")
                    
                    if cond_type == "価格変動(N%到達)":
                        direction = cnd.get('direction', "上昇")
                        target_pct = cnd.get('target_pct', 10.0) / 100.0
                        if direction == "上昇":
                            if future_df['High'].max() < t_price * (1.0 + target_pct): conditions_passed = False; break
                        else:
                            if future_df['Low'].min() > t_price * (1.0 - target_pct): conditions_passed = False; break
                            
                    elif cond_type == "直近高値・底値の更新":
                        update_target = cnd.get('update_target', "高値更新")
                        if update_target == "高値更新":
                            past_high = df_period.loc[:t_date, 'High'].max()
                            if pd.isna(past_high): past_high = df.loc[:t_date, 'High'].max()
                            if future_df['High'].max() <= past_high: conditions_passed = False; break
                        else:
                            past_low = df_period.loc[:t_date, 'Low'].min()
                            if pd.isna(past_low): past_low = df.loc[:t_date, 'Low'].min()
                            if future_df['Low'].min() >= past_low: conditions_passed = False; break
                            
                if conditions_passed and len(when.get('conditions', [])) > 0:
                    completed_cycles += 1

        # --- 3. 発生回数(Occurrence)の評価 ---
        if completed_cycles < l_required_cycles:
            return False
                
    return True