import os
import glob
import re
import pandas as pd
import streamlit as st
from PIL import Image
import qrcode
from streamlit_option_menu import option_menu

# --- データ読み込み用共通関数 ---
@st.cache_data
def load_all_data():
    """リポジトリ内の全Excelファイル（character_master.xlsx, 問題集.xlsx など）を統合して読み込む"""
    files = glob.glob("*.xlsx")
    if not files:
        return pd.DataFrame()
    
    df_list = []
    for f in files:
        try:
            temp_df = pd.read_excel(f)
            temp_df["source_file"] = f
            df_list.append(temp_df)
        except Exception:
            continue
            
    if not df_list:
        return pd.DataFrame()
        
    merged_df = pd.concat(df_list, ignore_index=True)
    return merged_df

# --- ページ基本設定 ---
st.set_page_config(page_title="ONE PIECE ナレッジキング対策", page_icon="🏴‍☠️", layout="wide")

# --- サイドバーナビゲーション ---
with st.sidebar:
    st.header("🏴‍☠️ ナビセンター")
    selected = option_menu(
        menu_title=None,
        options=["ホーム", "テスト開始", "苦手克服", "AI検索モード", "データ追加"],
        icons=["house", "check-circle", "exclamation-triangle", "search", "plus-circle"],
        default_index=0,
    )

# 全データ取得
df_all = load_all_data()

# --- 1. ホーム画面 ---
if selected == "ホーム":
    st.markdown("""
        <div style="border:2px solid #333; padding:20px; border-radius:10px; text-align:center;">
            <h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1>
            <p>最強のデータベースを脳に刻め</p>
        </div>
    """, unsafe_allow_html=True)
    st.write("")
    if df_all.empty:
        st.warning("現在、読み込めるExcelデータ（.xlsx）がありません。GitHubにExcelファイルをアップロードしてください。")
    else:
        st.info(f"👈 左側のメニューから機能を選択してください。（登録済データ: {len(df_all)} 件）")

# --- 2. テスト開始 ---
elif selected == "テスト開始":
    st.subheader("📝 クイズテスト")
    if df_all.empty:
        st.warning("出題できるデータ（character_master.xlsx または 問題集.xlsx）が空っぽです。")
    else:
        st.success(f"全 {len(df_all)} 問の中からランダムに出題可能です。")

# --- 3. 苦手克服 ---
elif selected == "苦手克服":
    st.subheader("🔥 苦手克服モード")
    st.info("間違えた問題やチェックした問題を重点的に復習できます。")

# --- 4. AI検索モード ---
elif selected == "AI検索モード":
    st.title("🔍 AI検索モード")
    st.caption("〜 キャラクターマスタ爆速逆引き図鑑 〜")
    st.write("---")
    
    if df_all.empty:
        st.error("『character_master.xlsx』または該当するExcelデータが見つかりません。")
    else:
        search_query = st.text_input("キーワード検索（名前・悪魔の実・技・所属・エピソードなど）", "", placeholder="例: ルフィ、ゴムゴムの実、インペルダウン")
        
        if search_query:
            mask = df_all.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
            results = df_all[mask]
            st.write(f"検索結果: **{len(results)}** 件")
            if not results.empty:
                st.dataframe(results, use_container_width=True)
            else:
                st.warning("該当するデータが見つかりませんでした。")
        else:
            st.write("上部の検索窓にキーワードを入力してください。")
            st.dataframe(df_all.head(20), use_container_width=True)

# --- 5. データ追加（機能拡張版）---
elif selected == "データ追加":
    st.title("➕ データ追加")
    st.caption("新しい問題データやキャラクター情報をフォームから直接登録・書き出しができます。")
    st.write("---")
    
    # 既存のカラム構成を取得（なければデフォルト項目を設定）
    if not df_all.empty:
        # source_file カラムを除いた項目リスト
        columns = [c for c in df_all.columns if c != "source_file"]
    else:
        columns = ["問題", "解答", "解説", "ジャンル", "難易度"]
        
    st.subheader("1. フォーム入力による新規追加")
    
    with st.form("add_data_form", clear_on_submit=True):
        input_data = {}
        for col in columns:
            input_data[col] = st.text_input(f"{col}")
            
        submitted = st.form_submit_button("データをセッションに追加")
        
        if submitted:
            new_row = pd.DataFrame([input_data])
            if "added_data" not in st.session_state:
                st.session_state["added_data"] = pd.DataFrame()
            
            st.session_state["added_data"] = pd.concat([st.session_state["added_data"], new_row], ignore_index=True)
            st.success("セッションに一時保存しました！")
            
    # 追加データの確認とファイル出力
    if "added_data" in st.session_state and not st.session_state["added_data"].empty:
        st.write("---")
        st.subheader("2. 今回追加したデータ一覧（一時保存中）")
        st.dataframe(st.session_state["added_data"], use_container_width=True)
        
        # Excelとしてダウンロードするボタン（GitHub更新用）
        output_filename = "added_quiz_data.xlsx"
        
        # メモリ上でExcelファイルを作成
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state["added_data"].to_excel(writer, index=False)
            
        st.download_button(
            label="📥 追加データをExcelファイルとしてダウンロード",
            data=buffer.getvalue(),
            file_name=output_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.caption("※ダウンロードした `added_quiz_data.xlsx` をGitHubにドラッグ＆ドロップすると、アプリ全体に永続反映されます。")
