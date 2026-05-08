import streamlit as st
import json
import base64
import zlib

# 保存・保護すべき第一層（ベース環境フィルター）の固定キー一覧
BASE_FILTER_KEYS = [
    'global_ma_short', 'global_ma_mid', 'global_ma_long',
    'master_sector', 'target_sectors','use_theme_filter', 'target_themes',
    'use_per_filter', 'min_per_chk', 'min_per', 'max_per_chk', 'max_per',
    'use_pbr_filter', 'min_pbr_chk', 'min_pbr', 'max_pbr_chk', 'max_pbr',
    'use_roe_filter', 'min_roe_chk', 'min_roe', 'max_roe_chk', 'max_roe',
    'use_div_filter', 'min_div_chk', 'min_div', 'max_div_chk', 'max_div',
    'use_mcap_filter', 'min_mcap_chk', 'min_mcap', 'max_mcap_chk', 'max_mcap',
    'use_period_growth', 'min_g_chk', 'min_growth_pct', 'max_g_chk', 'max_growth_pct',
    'use_volume_filter', 'min_v_chk', 'min_volume', 'max_v_chk', 'max_volume',
    'use_trend_filter'
]

def encode_full_state():
    """アクションブロック、ベースフィルター、および個別の業種チェック状態を暗号化します"""
    export_data = {
        "conditions": st.session_state.get("conditions", []),
        "base_filters": {}
    }
    
    for key in BASE_FILTER_KEYS:
        if key in st.session_state:
            export_data["base_filters"][key] = st.session_state[key]
            
    sector_states = {k: v for k, v in st.session_state.items() if k.startswith("sec_")}
    export_data["sector_states"] = sector_states
            
    json_str = json.dumps(export_data)
    compressed = zlib.compress(json_str.encode('utf-8'))
    b64_str = base64.urlsafe_b64encode(compressed).decode('utf-8')
    return b64_str

def decode_full_state(b64_str):
    """暗号コードからシステム全体の状態を安全に復元します"""
    if not b64_str:
        return None, "コードが入力されていません。"
        
    try:
        clean_str = b64_str.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        compressed = base64.urlsafe_b64decode(clean_str)
        json_str = zlib.decompress(compressed).decode('utf-8')
        data = json.loads(json_str)
        
        if isinstance(data, list):
            return {"conditions": data, "base_filters": {}, "sector_states": {}}, "success"
        else:
            return data, "success"
            
    except Exception as e:
        return None, f"復元に失敗しました: {str(e)}"

def render_sidebar():
    """サイドバー（復活の呪文UI）を描画し、状態の入出力を処理します"""
    with st.sidebar:
        st.header("💾 条件コードの出力／読込")
        st.caption("作成した条件を文字列として出力し、保存・復元できます。")
        
        st.divider()
        
        st.subheader("📤 現在の条件を出力")
        if st.button("共有コードを発行する", use_container_width=True):
            if len(st.session_state.get("conditions", [])) == 0:
                st.warning("アクションブロックがありません。")
            else:
                export_code = encode_full_state()
                st.success("以下のコードをコピーして保存してください！")
                st.text_area("あなたの条件コード", value=export_code, height=150)
                st.caption("※このコードには第一層の詳細設定もすべて含まれています。")

        st.divider()
        
        st.subheader("📥 コードから条件を復元")
        import_code = st.text_area("復元したいコードを貼り付けてください", height=100)
        if st.button("このコードを読み込む", use_container_width=True):
            if import_code:
                restored_data, status_message = decode_full_state(import_code)
                
                if restored_data is not None:
                    st.session_state.conditions = restored_data.get("conditions", [])
                    
                    base_filters = restored_data.get("base_filters", {})
                    for key, value in base_filters.items():
                        st.session_state[key] = value
                    
                    sector_states = restored_data.get("sector_states", {})
                    for key, value in sector_states.items():
                        st.session_state[key] = value
                    
                    safe_keys = [
                        'conditions', 'selected_stocks', 'target_start', 'target_end', 
                        'df_results_raw', 'buy_conditions', 'sell_conditions', 'global_ma'
                    ] + BASE_FILTER_KEYS + list(sector_states.keys())
                    
                    for k in list(st.session_state.keys()):
                        if k not in safe_keys:
                            del st.session_state[k]
                        
                    st.success("システム全体の復元に成功しました！画面を更新します。")
                    st.rerun()
                else:
                    st.error(f"復元エラー: {status_message}")
            else:
                st.warning("コードを入力してください。")