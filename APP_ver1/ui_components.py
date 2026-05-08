import streamlit as st

# =========================================================
# 1. ベース環境フィルターのUI（完全同期版）
# =========================================================
def render_base_filters(df_list, global_ma_short, global_ma_mid, global_ma_long):
    st.subheader("2. 【第1層】ベース環境フィルター（数値・属性条件）")

    st.session_state.setdefault('master_sector', True)
    st.session_state.setdefault('use_trend_filter', True)
    st.session_state.setdefault('use_volume_filter', True)

    # ★ 改修ポイント1：CSVの「テーマ」列から、選択肢となる全テーマを自動抽出します
    available_themes = []
    if not df_list.empty and 'テーマ' in df_list.columns:
        themes_series = df_list['テーマ'].dropna()
        # "、" 区切りで分割し、空文字を除外して一意のリスト（重複なし）を作成します
        all_themes_flat = [theme.strip() for sublist in themes_series.str.split('、') for theme in sublist if theme.strip()]
        available_themes = sorted(list(set(all_themes_flat)))

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.write("**■ 企業属性・テーマ・ファンダメンタルズ**")
        
        # ★ 改修ポイント2：テーマ選択用UIの描画
        use_theme_filter = False
        target_themes = []
        if available_themes:
            use_theme_filter = st.checkbox("特定のテーマで絞り込む", key="use_theme_filter")
            if use_theme_filter:
                with st.container(border=True):
                    st.caption("資金流入が期待できるテーマを選択してください。")
                    target_themes = st.multiselect("対象テーマを選択（複数可）", available_themes, key="target_themes")
        else:
            st.caption("※CSVにテーマ列が存在しないため、テーマ検索は無効化されています。")
            
        st.write("---")
        
        if not df_list.empty and '業種' in df_list.columns:
            all_sectors = sorted(df_list['業種'].dropna().unique().tolist())
            select_all = st.checkbox("すべての業種を選択", key="master_sector")
            target_sectors = []
            if select_all:
                target_sectors = all_sectors
            else:
                with st.expander("業種リストを個別に選択", expanded=True):
                    sec_col1, sec_col2 = st.columns(2)
                    for idx, sector in enumerate(all_sectors):
                        target_col = sec_col1 if idx % 2 == 0 else sec_col2
                        if target_col.checkbox(sector, key=f"sec_{sector}"):
                            target_sectors.append(sector)
            st.session_state['target_sectors'] = target_sectors
        else:
            target_sectors = []
            select_all = True

        st.write("---")
        
        use_per_filter = st.checkbox("PER（株価収益率）で絞り込む", key="use_per_filter")
        if use_per_filter:
            with st.container(border=True):
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    has_min_per = st.checkbox("下限設定", key="min_per_chk")
                    min_per = st.number_input("最低PER", step=0.5, key="min_per") if has_min_per else None
                with p_col2:
                    has_max_per = st.checkbox("上限設定", key="max_per_chk")
                    max_per = st.number_input("最高PER", step=0.5, key="max_per") if has_max_per else None
        else: min_per = max_per = None

        use_pbr_filter = st.checkbox("PBR（株価純資産倍率）で絞り込む", key="use_pbr_filter")
        if use_pbr_filter:
            with st.container(border=True):
                pb_col1, pb_col2 = st.columns(2)
                with pb_col1:
                    has_min_pbr = st.checkbox("下限設定", key="min_pbr_chk")
                    min_pbr = st.number_input("最低PBR", step=0.1, key="min_pbr") if has_min_pbr else None
                with pb_col2:
                    has_max_pbr = st.checkbox("上限設定", key="max_pbr_chk")
                    max_pbr = st.number_input("最高PBR", step=0.1, key="max_pbr") if has_max_pbr else None
        else: min_pbr = max_pbr = None

        use_roe_filter = st.checkbox("ROE（自己資本利益率）で絞り込む", key="use_roe_filter")
        if use_roe_filter:
            with st.container(border=True):
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    has_min_roe = st.checkbox("下限設定", key="min_roe_chk")
                    min_roe = st.number_input("最低ROE (%)", step=1.0, key="min_roe") if has_min_roe else None
                with r_col2:
                    has_max_roe = st.checkbox("上限設定", key="max_roe_chk")
                    max_roe = st.number_input("最高ROE (%)", step=1.0, key="max_roe") if has_max_roe else None
        else: min_roe = max_roe = None

        use_div_filter = st.checkbox("配当利回りで絞り込む", key="use_div_filter")
        if use_div_filter:
            with st.container(border=True):
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    has_min_div = st.checkbox("下限設定", key="min_div_chk")
                    min_div = st.number_input("最低利回り (%)", step=0.1, key="min_div") if has_min_div else None
                with d_col2:
                    has_max_div = st.checkbox("上限設定", key="max_div_chk")
                    max_div = st.number_input("最高利回り (%)", step=0.1, key="max_div") if has_max_div else None
        else: min_div = max_div = None

    with col_b2:
        st.write("**■ テクニカル環境・規模（トレンド・流動性）**")
        
        use_mcap_filter = st.checkbox("時価総額で絞り込む（企業規模）", key="use_mcap_filter")
        if use_mcap_filter:
            with st.container(border=True):
                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    has_min_mcap = st.checkbox("下限設定", key="min_mcap_chk")
                    min_mcap = st.number_input("最低時価総額 (億円)", step=50.0, key="min_mcap") * 100000000 if has_min_mcap else None
                with m_col2:
                    has_max_mcap = st.checkbox("上限設定", key="max_mcap_chk")
                    max_mcap = st.number_input("最高時価総額 (億円)", step=100.0, key="max_mcap") * 100000000 if has_max_mcap else None
        else: min_mcap = max_mcap = None

        use_trend_filter = st.checkbox("長期上昇トレンド（最新株価が200日SMAより上）に限定する", key="use_trend_filter")
        
        use_period_growth = st.checkbox("期間内の全体値上がり率で絞り込む", key="use_period_growth")
        if use_period_growth:
            with st.container(border=True):
                g_col1, g_col2 = st.columns(2)
                with g_col1: 
                    has_min_growth = st.checkbox("下限設定", key="min_g_chk")
                    min_growth_pct = st.number_input("最低値上がり率 (%)", step=1.0, key="min_growth_pct") if has_min_growth else None
                with g_col2: 
                    has_max_growth = st.checkbox("上限設定", key="max_g_chk")
                    max_growth_pct = st.number_input("最高値上がり率 (%)", step=1.0, key="max_growth_pct") if has_max_growth else None
        else: min_growth_pct = max_growth_pct = None
        
        use_volume_filter = st.checkbox("指定期間の1日平均出来高で絞り込む", key="use_volume_filter")
        if use_volume_filter:
            with st.container(border=True):
                v_col1, v_col2 = st.columns(2)
                with v_col1: 
                    has_min_vol = st.checkbox("下限設定", key="min_v_chk")
                    min_volume = st.number_input("最低平均出来高 (株)", step=10000.0, key="min_volume") if has_min_vol else None
                with v_col2: 
                    has_max_vol = st.checkbox("上限設定", key="max_v_chk")
                    max_volume = st.number_input("最高平均出来高 (株)", step=10000.0, key="max_volume") if has_max_vol else None
        else: min_volume = max_volume = None

    # ★ 改修ポイント3：メインプログラムに渡す辞書にテーマ設定を追加します
    return {
        "global_ma_short": global_ma_short,
        "global_ma_mid": global_ma_mid,
        "global_ma_long": global_ma_long,
        "use_theme_filter": use_theme_filter,
        "target_themes": target_themes,
        "use_sector_filter": not select_all,
        "target_sectors": target_sectors,
        "use_per_filter": use_per_filter, "min_per": min_per, "max_per": max_per,
        "use_pbr_filter": use_pbr_filter, "min_pbr": min_pbr, "max_pbr": max_pbr,
        "use_roe_filter": use_roe_filter, "min_roe": min_roe, "max_roe": max_roe,
        "use_div_filter": use_div_filter, "min_div": min_div, "max_div": max_div,
        "use_mcap_filter": use_mcap_filter, "min_mcap": min_mcap, "max_mcap": max_mcap,
        "use_trend_filter": use_trend_filter,
        "use_period_growth": use_period_growth, "min_growth_pct": min_growth_pct, "max_growth_pct": max_growth_pct,
        "use_volume_filter": use_volume_filter, "min_volume": min_volume, "max_volume": max_volume
    }

# =========================================================
# 2. アクション・トリガー（カスタムUI）の描画
# =========================================================
AVAILABLE_ACTIONS = [
    "【カスタム】",
    "ゴールデンクロス（SMA）",
    "株価のSMA上抜け",
    "RSI（指定値以下で反発）",
    "MACD（ゼロライン浮上）",
    "ボリンジャーバンド（-2σタッチ）"
]

def render_action_triggers():
    st.subheader("3. 【第1.5層〜第3層】アクション・トリガーとバックテスト")

    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        new_cond_type = st.selectbox("追加するアクションをリストから選択してください", AVAILABLE_ACTIONS)
    with col_add2:
        st.write("") 
        if st.button("＋ このアクションを追加", use_container_width=True):
            new_cond = {"type": new_cond_type, "operator": "AND" if len(st.session_state.conditions) > 0 else None, "params": {}, "advanced": {}}
            if new_cond_type == "【カスタム】":
                new_cond["occurrences"] = [] 
            elif new_cond_type == "ゴールデンクロス（SMA）":
                new_cond["params"] = {"short": 5, "long": 25}; new_cond["advanced"] = {"use_occ": True, "min_occ": 1, "use_perf": True, "check_days": 40, "target_pct": 15.0, "use_stop_loss": True, "stop_loss_pct": 5.0}
            elif new_cond_type == "株価のSMA上抜け":
                new_cond["params"] = {"period": 25}; new_cond["advanced"] = {"use_occ": True, "min_occ": 1, "use_perf": True, "check_days": 20, "target_pct": 10.0, "use_stop_loss": True, "stop_loss_pct": 4.0}
            elif new_cond_type == "RSI（指定値以下で反発）":
                new_cond["params"] = {"period": 14, "threshold": 30}; new_cond["advanced"] = {"use_occ": True, "min_occ": 1, "use_perf": True, "check_days": 10, "target_pct": 5.0, "use_stop_loss": True, "stop_loss_pct": 3.0}
            elif new_cond_type == "MACD（ゼロライン浮上）":
                new_cond["advanced"] = {"use_occ": True, "min_occ": 1, "use_perf": True, "check_days": 20, "target_pct": 10.0, "use_stop_loss": True, "stop_loss_pct": 5.0}
            elif new_cond_type == "ボリンジャーバンド（-2σタッチ）":
                new_cond["params"] = {"period": 20}; new_cond["advanced"] = {"use_occ": True, "min_occ": 1, "use_perf": True, "check_days": 15, "target_pct": 8.0, "use_stop_loss": True, "stop_loss_pct": 4.0}
                
            st.session_state.conditions.append(new_cond)
            st.rerun()

    if len(st.session_state.conditions) == 0:
        st.info("アクションブロックがありません。「＋」ボタンから追加してください。")
    else:
        for i, cond in enumerate(st.session_state.conditions):
            with st.container(border=True):
                col_title, col_del = st.columns([4, 1])
                with col_title: st.markdown(f"#### ブロック {i+1}: {cond['type']}")
                with col_del:
                    if st.button("🗑️ 削除", key=f"del_btn_{i}", use_container_width=True):
                        st.session_state.conditions.pop(i)
                        st.rerun()
                
                if i > 0:
                    op_opts = ["AND", "OR"]
                    op_val = cond.get('operator', "AND")
                    op_idx = op_opts.index(op_val) if op_val in op_opts else 0
                    cond['operator'] = st.radio(f"ブロック{i}との論理結合", op_opts, index=op_idx, key=f"op_{i}", horizontal=True)
                
                if cond['type'] == "【カスタム】":
                    st.caption("回数 ＞ When ＞ 条件 の順にモジュールを追加してロジックを構成します。")
                    
                    if st.button("＋ 【回数】モジュールを追加", key=f"add_occ_{i}"):
                        cond.setdefault('occurrences', []).append({"l_times": 2, "whens": []})
                        st.rerun()

                    for o_idx, occ in enumerate(cond.get('occurrences', [])):
                        with st.container(border=True):
                            o_c1, o_c2 = st.columns([4, 1])
                            with o_c1: st.markdown(f"**📦 発生回数モジュール {o_idx+1}**")
                            with o_c2:
                                if st.button("🗑️ 削除", key=f"del_occ_{i}_{o_idx}", use_container_width=True):
                                    cond['occurrences'].pop(o_idx)
                                    st.rerun()

                            occ['l_times'] = st.number_input("最低サイクル数 (L回)", 1, 100, int(occ.get('l_times', 2)), key=f"occ_l_{i}_{o_idx}")
                            
                            if st.button("＋ 【When】モジュールを追加", key=f"add_when_{i}_{o_idx}"):
                                occ['whens'].append({
                                    "when_type": "スイング(山・谷)", "target_type": "底値", "swing_window": 5,
                                    "ma_fast": "短期MA", "ma_slow": "中期MA", "cross_direction": "ゴールデンクロス",
                                    "use_pullback": True, "min_o_pct": 3.0, "max_o_pct": 8.0, "o_direction": "下落(押し目)",
                                    "use_recovery": False, "recovery_days": 10,
                                    "conditions": []
                                })
                                st.rerun()
                                
                            for w_idx, when in enumerate(occ.get('whens', [])):
                                with st.container(border=True):
                                    c2 = st.columns([0.05, 0.95])[1]
                                    with c2:
                                        w_c1, w_c2 = st.columns([4, 1])
                                        with w_c1: st.markdown(f"**⏱️ Whenモジュール {w_idx+1} （起点の定義）**")
                                        with w_c2:
                                            if st.button("🗑️ 削除", key=f"del_when_{i}_{o_idx}_{w_idx}", use_container_width=True):
                                                occ['whens'].pop(w_idx)
                                                st.rerun()
                                        
                                        w_opts = ["スイング(山・谷)", "MAクロス"]
                                        w_val = when.get('when_type', "スイング(山・谷)")
                                        w_idx_opt = w_opts.index(w_val) if w_val in w_opts else 0
                                        when['when_type'] = st.selectbox("Whenのロジックを選択", w_opts, index=w_idx_opt, key=f"when_type_{i}_{o_idx}_{w_idx}")
                                        
                                        if when['when_type'] == "スイング(山・谷)":
                                            wx1, wx2 = st.columns(2)
                                            t_opts = ["高値", "底値"]
                                            t_val = when.get('target_type', "底値")
                                            t_idx = t_opts.index(t_val) if t_val in t_opts else 1
                                            with wx1: when['target_type'] = st.radio("到達ターゲット", t_opts, index=t_idx, horizontal=True, key=f"when_t_{i}_{o_idx}_{w_idx}")
                                            with wx2: when['swing_window'] = st.number_input("山/谷の判定期間 (前後N日間)", 1, 30, int(when.get('swing_window', 5)), key=f"when_sw_{i}_{o_idx}_{w_idx}")
                                            
                                        elif when['when_type'] == "MAクロス":
                                            st.caption("グローバル設定した3本のMAから、交差させる線を選択します。")
                                            ma_c1, ma_c2 = st.columns(2)
                                            ma_opts = ["短期MA", "中期MA", "長期MA"]
                                            ma_f_val = when.get('ma_fast', "短期MA")
                                            ma_s_val = when.get('ma_slow', "中期MA")
                                            ma_f_idx = ma_opts.index(ma_f_val) if ma_f_val in ma_opts else 0
                                            ma_s_idx = ma_opts.index(ma_s_val) if ma_s_val in ma_opts else 1
                                            with ma_c1: when['ma_fast'] = st.radio("交差する線（主線）", ma_opts, index=ma_f_idx, horizontal=True, key=f"ma_f_{i}_{o_idx}_{w_idx}")
                                            with ma_c2: when['ma_slow'] = st.radio("基準となる線（抵抗線）", ma_opts, index=ma_s_idx, horizontal=True, key=f"ma_s_{i}_{o_idx}_{w_idx}")
                                            
                                            d_opts = ["ゴールデンクロス", "デッドクロス"]
                                            d_val = when.get('cross_direction', "ゴールデンクロス")
                                            d_idx = d_opts.index(d_val) if d_val in d_opts else 0
                                            when['cross_direction'] = st.selectbox("交差方向", d_opts, index=d_idx, key=f"ma_d_{i}_{o_idx}_{w_idx}")
                                            
                                            st.write("---")
                                            st.markdown("**■ クロス後の詳細検証（Whenの確定条件）**")
                                            
                                            when['use_pullback'] = st.checkbox("特定の変動率（押し目・戻り）を通過すること", value=when.get('use_pullback', True), key=f"use_pb_{i}_{o_idx}_{w_idx}")
                                            if when['use_pullback']:
                                                with st.container(border=True):
                                                    pb_c1, pb_c2, pb_c3 = st.columns(3)
                                                    od_opts = ["下落(押し目)", "上昇(戻り)"]
                                                    od_val = when.get('o_direction', "下落(押し目)")
                                                    od_idx = od_opts.index(od_val) if od_val in od_opts else 0
                                                    with pb_c1: when['o_direction'] = st.selectbox("方向", od_opts, index=od_idx, key=f"ma_od_{i}_{o_idx}_{w_idx}")
                                                    with pb_c2: when['min_o_pct'] = st.number_input("最低変動率 (%)", -100.0, 100.0, float(when.get('min_o_pct', 3.0)), key=f"ma_omin_{i}_{o_idx}_{w_idx}")
                                                    with pb_c3: when['max_o_pct'] = st.number_input("最大許容変動率 (%)", -100.0, 100.0, float(when.get('max_o_pct', 8.0)), key=f"ma_omax_{i}_{o_idx}_{w_idx}")
                                            
                                            when['use_recovery'] = st.checkbox("N日以内にトレンドを回復すること", value=when.get('use_recovery', False), key=f"use_rec_{i}_{o_idx}_{w_idx}")
                                            if when['use_recovery']:
                                                with st.container(border=True):
                                                    re_c1, re_c2 = st.columns(2)
                                                    with re_c1: when['recovery_days'] = st.number_input("回復猶予期間 (N日以内)", 1, 100, int(when.get('recovery_days', 10)), key=f"ma_rd_{i}_{o_idx}_{w_idx}")
                                        
                                        if st.button("＋ 【条件(シグナル)】モジュールを追加", key=f"add_cond_{i}_{o_idx}_{w_idx}"):
                                            when['conditions'].append({"cond_type": "価格変動(N%到達)", "direction": "上昇", "target_pct": 10.0, "update_target": "高値更新"})
                                            st.rerun()
                                            
                                        for c_idx, cnd in enumerate(when.get('conditions', [])):
                                            with st.container(border=True):
                                                cc2 = st.columns([0.05, 0.95])[1]
                                                with cc2:
                                                    c_c1, c_c2 = st.columns([4, 1])
                                                    with c_c1: st.markdown(f"**🎯 条件モジュール {c_idx+1} （起点通過後の達成条件）**")
                                                    with c_c2:
                                                        if st.button("🗑️ 削除", key=f"del_cond_{i}_{o_idx}_{w_idx}_{c_idx}", use_container_width=True):
                                                            when['conditions'].pop(c_idx)
                                                            st.rerun()
                                                    
                                                    c_opts = ["価格変動(N%到達)", "直近高値・底値の更新"]
                                                    cv_val = cnd.get('cond_type', "価格変動(N%到達)")
                                                    cv_idx = c_opts.index(cv_val) if cv_val in c_opts else 0
                                                    cnd['cond_type'] = st.selectbox("条件のロジックを選択", c_opts, index=cv_idx, key=f"cnd_type_{i}_{o_idx}_{w_idx}_{c_idx}")
                                                    
                                                    if cnd['cond_type'] == "価格変動(N%到達)":
                                                        cx1, cx2 = st.columns(2)
                                                        dir_opts = ["上昇", "下降"]
                                                        dir_val = cnd.get('direction', "上昇")
                                                        dir_idx = dir_opts.index(dir_val) if dir_val in dir_opts else 0
                                                        with cx1: cnd['direction'] = st.selectbox("変動方向", dir_opts, index=dir_idx, key=f"cnd_d_{i}_{o_idx}_{w_idx}_{c_idx}")
                                                        with cx2: cnd['target_pct'] = st.number_input("目標(%)", 0.1, 100.0, float(cnd.get('target_pct', 10.0)), key=f"cnd_p_{i}_{o_idx}_{w_idx}_{c_idx}")
                                                    elif cnd['cond_type'] == "直近高値・底値の更新":
                                                        u_opts = ["高値更新", "底値更新"]
                                                        u_val = cnd.get('update_target', "高値更新")
                                                        u_idx = u_opts.index(u_val) if u_val in u_opts else 0
                                                        cnd['update_target'] = st.radio("更新ターゲット", u_opts, index=u_idx, horizontal=True, key=f"cnd_upd_{i}_{o_idx}_{w_idx}_{c_idx}")
                
                else:
                    st.markdown("**■ 基本パラメータ**")
                    p_cols = st.columns(3)
                    if cond['type'] == "ゴールデンクロス（SMA）":
                        with p_cols[0]: cond['params']['short'] = st.number_input("短期SMA期間", 1, 100, int(cond['params'].get('short', 5)), key=f"s_{i}")
                        with p_cols[1]: cond['params']['long'] = st.number_input("長期SMA期間", 10, 300, int(cond['params'].get('long', 25)), key=f"l_{i}")
                    elif cond['type'] == "株価のSMA上抜け":
                        with p_cols[0]: cond['params']['period'] = st.number_input("基準となるSMA期間", 1, 300, int(cond['params'].get('period', 25)), key=f"break_{i}")
                    elif cond['type'] == "RSI（指定値以下で反発）":
                        with p_cols[0]: cond['params']['period'] = st.number_input("RSI計算期間", 1, 50, int(cond['params'].get('period', 14)), key=f"rp_{i}")
                        with p_cols[1]: cond['params']['threshold'] = st.number_input("閾値（これ以下）", 1, 100, int(cond['params'].get('threshold', 30)), key=f"rt_{i}")
                    elif cond['type'] == "ボリンジャーバンド（-2σタッチ）":
                        with p_cols[0]: cond['params']['period'] = st.number_input("計算期間", 1, 100, int(cond['params'].get('period', 20)), key=f"bb_{i}")
                    elif cond['type'] == "MACD（ゼロライン浮上）":
                        st.write("※MACDは標準パラメータ(12, 26, 9)で計算されます。")

                    with st.expander("■ 第3層：検証要件（発生頻度と利確・損切り）", expanded=False):
                        col_v1, col_v2 = st.columns(2)
                        with col_v1:
                            use_occ = st.checkbox("最低発生回数を指定する", value=cond['advanced'].get('use_occ', True), key=f"use_occ_{i}")
                            cond['advanced']['use_occ'] = use_occ
                            if use_occ: cond['advanced']['min_occ'] = st.number_input("最低回数", 1, 100, int(cond['advanced'].get('min_occ', 1)), key=f"occ_{i}")
                        
                        with col_v2:
                            use_perf = st.checkbox("シグナル後の値上がり（バックテスト）を検証する", value=cond['advanced'].get('use_perf', True), key=f"use_perf_{i}")
                            cond['advanced']['use_perf'] = use_perf
                            
                        if use_perf:
                            a_cols = st.columns(3)
                            with a_cols[0]: cond['advanced']['check_days'] = st.number_input("検証日数", 1, 100, int(cond['advanced'].get('check_days', 20)), key=f"chk_{i}")
                            with a_cols[1]: cond['advanced']['target_pct'] = st.number_input("目標利確ライン(%)", 1.0, 100.0, float(cond['advanced'].get('target_pct', 10.0)), key=f"pct_{i}")
                            with a_cols[2]: 
                                use_stop = st.checkbox("損切りラインを有効化", value=cond['advanced'].get('use_stop_loss', True), key=f"use_stop_{i}")
                                cond['advanced']['use_stop_loss'] = use_stop
                                if use_stop: cond['advanced']['stop_loss_pct'] = st.number_input("損切りライン(%)", 1.0, 50.0, float(cond['advanced'].get('stop_loss_pct', 5.0)), key=f"stop_{i}")
            
        if st.button("ブロックをすべてクリア", type="secondary"):
            st.session_state.conditions = []
            st.rerun()

    st.divider()