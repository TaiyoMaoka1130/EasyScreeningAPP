import streamlit as st
import pandas as pd
import datetime
import os
import json
import io
import base64  # ★追加
import zlib    # ★追加
from screening_engine import run_screening


# =========================================================
# ★コードによる条件の書き出し／読み込み機能
# =========================================================
def encode_conditions(conditions):
    """現在の条件を圧縮された文字列コードに変換する"""
    if not conditions:
        return ""
    json_str = json.dumps(conditions)
    compressed = zlib.compress(json_str.encode('utf-8'))
    b64_str = base64.b64encode(compressed).decode('utf-8')
    return b64_str

def decode_conditions(b64_str):
    """文字列コードから条件を復元する"""
    try:
        compressed = base64.b64decode(b64_str)
        json_str = zlib.decompress(compressed).decode('utf-8')
        return json.loads(json_str)
    except Exception:
        return None # 失敗した場合はNoneを返す

# 新しく作った部品（モジュール）を読み込む
from state_manager import render_sidebar
from ui_components import render_base_filters, render_action_triggers

st.set_page_config(page_title="Quant Screener", layout="wide")

# =========================================================
# 初期設定
# =========================================================
LIST_DIR = "APP_ver1\stucklists" # リストのディレクトリ

if "conditions" not in st.session_state:
    st.session_state.conditions = []

# =========================================================
# 1. UIコンポーネントの呼び出し
# =========================================================
# サイドバー（保存機能）の描画
render_sidebar()

# 全体設定の描画
st.subheader("1. ターゲット市場と検証期間・全体設定")
st.markdown("**■ 検証期間の設定**")
col_m, col_s, col_e = st.columns(3)
with col_m: target_market = st.selectbox("解析リスト", ("日経225.csv", "modified_topixweight_j.csv", "NYdaw.csv", "S&P500.csv"))
with col_s: start_date = st.date_input("検証開始日", datetime.date(2026, 1, 1))
with col_e: end_date = st.date_input("検証終了日", datetime.date.today())

st.markdown("**■ 移動平均線（MA）のグローバル設定**")
st.caption("システム全体で使用する基準となる3本のMA日数を設定します。")
ma_col1, ma_col2, ma_col3 = st.columns(3)
with ma_col1: global_ma_short = st.number_input("短期MA (日)", 1, 100, 5)
with ma_col2: global_ma_mid   = st.number_input("中期MA (日)", 1, 200, 25)
with ma_col3: global_ma_long  = st.number_input("長期MA (日)", 1, 300, 75)

# リストの読み込み
file_path = os.path.join(LIST_DIR, target_market)
df_list = pd.read_csv(file_path, encoding="utf-8-sig") if os.path.exists(file_path) else pd.DataFrame()
st.divider()

# ベースフィルターの描画（選択された辞書を受け取る）
base_filters = render_base_filters(df_list, global_ma_short, global_ma_mid, global_ma_long)
st.divider()

# アクション・トリガーの描画
render_action_triggers()

# --- 4. スクリーニング実行と結果表示 ---
st.subheader("4. スクリーニング実行")

# セッション状態の初期化
if "df_results_raw" not in st.session_state:
    st.session_state.df_results_raw = None

if st.button("スクリーニングを開始する", type="primary", use_container_width=True):
    
    if base_filters.get('use_theme_filter') and base_filters.get('target_themes'):
                themes = base_filters['target_themes']
                # 選択された複数のテーマのいずれかに合致するか判定（OR検索）
                pattern = '|'.join(themes)
                df_list = df_list[df_list['テーマ'].str.contains(pattern, na=False)]
    
    if df_list.empty:
        st.error("解析リストの読み込みに失敗しました。")
    else:
        tickers = df_list['コード'].astype(str).tolist()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total):
            progress_bar.progress(current / total)
            status_text.text(f"解析中... {current}/{total} 銘柄完了")
            
        st.session_state['global_ma'] = {
            "short": global_ma_short, "mid": global_ma_mid, "long": global_ma_long
        }
            
        # スクリーニング実行と結果の保存
        results = run_screening(tickers, start_date, end_date, base_filters, st.session_state.conditions, update_progress)
        
        if results and len(results) > 0:
            st.session_state.df_results_raw = pd.DataFrame(results)
            status_text.text(f"解析完了！ 条件に一致した銘柄：{len(results)}件")
        else:
            st.session_state.df_results_raw = None
            status_text.text("解析完了。条件に一致する銘柄はありませんでした。")
            st.warning("条件に一致する銘柄は見つかりませんでした。条件を少し緩めてみてください。")

# =========================================================
# 結果の描画ブロック（ボタンの外側に配置することで、再実行しても消えなくなります）
# =========================================================
if st.session_state.df_results_raw is not None:
    df_results = st.session_state.df_results_raw
    
    # 企業名と業種の紐付け
    name_col = '銘柄名' if '銘柄名' in df_list.columns else '企業名'
    df_merged = pd.merge(df_results, df_list[['コード', name_col, '業種']], left_on='銘柄コード', right_on='コード', how='left')
    
    df_display = df_merged[[name_col, '最新終値', '業種', 'コード']].copy()
    df_display.columns = ['企業名', '最新終値', '業種', 'コード']
    
    # チェックボックス用の列を追加
    if "selected_rows_state" not in st.session_state:
        df_display.insert(0, "選択", False)
    
    st.markdown("### 📈 スクリーニング結果一覧")
    st.caption("詳細分析を行いたい銘柄にチェックを入れ、下のボタンを押してください。")
    
    
    # =========================================================
    # ★ 改修ポイント1：全選択チェックボックスの追加
    # =========================================================
    if not df_display.empty:
        # ユーザーがチェックを入れたら、データフレームの「選択」列をすべてTrueで上書きする
        select_all = st.checkbox("✅ 抽出されたすべての銘柄を選択する", key="select_all_results")
        if select_all:
            df_display["選択"] = True
    else:
        select_all = False

    # データエディターの描画
    edited_df = st.data_editor(
        df_display,
        column_config={
            "選択": st.column_config.CheckboxColumn("選択", default=False, width="small"),
            "コード": st.column_config.TextColumn("コード", disabled=True),
            "企業名": st.column_config.TextColumn("企業名", disabled=True),
            "業種": st.column_config.TextColumn("業種", disabled=True),
            "最新終値": st.column_config.NumberColumn("最新終値", format="¥%d")
        },
        disabled=['企業名', '最新終値', '業種', 'コード'],
        use_container_width=True,
        # =========================================================
        # ★ 改修ポイント2：エディターの再描画（強制リフレッシュ）
        # Streamlitの仕様上、外部から値を上書きした際はkeyを変更して
        # 古いUIの記憶をリセットさせる必要があります。
        # =========================================================
        key=f"result_editor_{select_all}"
    )

    # チェックがTrueになっている行だけを抽出
    selected_rows = edited_df[edited_df["選択"] == True]
    
    col_act1, col_act2 = st.columns([1, 1])
    with col_act1:
        if st.button("🚀 選択した銘柄を別ページで詳しく見る", type="primary", use_container_width=True):
            if not selected_rows.empty:
                st.session_state['selected_stocks'] = selected_rows.to_dict('records')
                st.session_state['target_start'] = start_date
                st.session_state['target_end'] = end_date
                st.switch_page("pages/2_Selection_Viewer.py")
            else:
                st.warning("分析する銘柄を1つ以上選択してください。")

    st.divider()
    
    st.markdown("### 📥 スクリーニング結果の保存")
    dl_col1, dl_col2 = st.columns(2)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_display.to_excel(writer, index=False, sheet_name="Results")
    with dl_col1:
        st.download_button(label="📊 Excel形式で保存 (.xlsx)", data=buffer.getvalue(), file_name=f"screening_{datetime.date.today()}.xlsx", use_container_width=True)
        
    csv = df_display.to_csv(index=False).encode('utf-8-sig')
    with dl_col2:
        st.download_button(label="📄 CSV形式で保存 (.csv)", data=csv, file_name=f"screening_{datetime.date.today()}.csv", use_container_width=True)