import glob
import io
import os
import re
import pandas as pd
import qrcode
import streamlit as st
from PIL import Image
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
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策", page_icon="🏴‍☠️", layout="wide"
)

# --- サイドバーナビゲーション ---
with st.sidebar:
    st.header("🏴‍☠️ ナビセンター")
    selected = option_menu(
        menu_title=None,
        options=["ホーム", "テスト開始", "苦手克服", "AI検索モード", "データ追加"],
        icons=[
            "house",
            "check-circle",
            "exclamation-triangle",
            "search",
            "plus-circle",
        ],
        default_index=0,
    )

# 全データ取得
df_all = load_all_data()

# --- 1. ホーム画面 ---
if selected == "ホーム":
    st.markdown(
        """
        <div style="border:2px solid #333; padding:20px; border-radius:10px; text-align:center;">
            <h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1>
            <p>最強のデータベースを脳に刻め</p>
        </div>
    """,
        unsafe_allow_html=True,
    )
    st.write("")
    if df_all.empty:
        st.warning(
            "現在、読み込めるExcelデータ（.xlsx）がありません。GitHubにExcelファイルをアップロードしてください。"
        )
    else:
        st.info(
            f"👈 左側のメニューから機能を選択してください。（登録済データ: {len(df_all)} 件）"
        )

# --- 2. テスト開始 ---
elif selected == "テスト開始":
    st.subheader("📝 クイズテスト")
    if df_all.empty:
        st.warning(
            "出題できるデータ（character_master.xlsx または 問題集.xlsx）が空っぽです。"
        )
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
        st.error(
            "『character_master.xlsx』または該当するExcelデータが見つかりません。"
        )
    else:
        search_query = st.text_input(
            "キーワード検索（名前・悪魔の実・技・所属・エピソードなど）",
            "",
            placeholder="例: ルフィ、ゴムゴムの実、インペルダウン",
        )

        if search_query:
            mask = (
                df_all.astype(str)
                .apply(
                    lambda x: x.str.contains(
                        search_query, case=False, na=False
                    )
                )
                .any(axis=1)
            )
            results = df_all[mask]
            st.write(f"検索結果: **{len(results)}** 件")
            if not results.empty:
                st.dataframe(results, use_container_width=True)
            else:
                st.warning("該当するデータが見つかりませんでした。")
        else:
            st.write("上部の検索窓にキーワードを入力してください。")
            st.dataframe(df_all.head(20), use_container_width=True)

# --- 5. データ追加（マルチバリエーション対応版）---
elif selected == "データ追加":
    st.title("➕ データ追加")
    st.caption(
        "問題のタイプに合わせて専用フォームから登録・Excel出力ができます。"
    )
    st.write("---")

    # セッション状態の初期化
    if "added_data" not in st.session_state:
        st.session_state["added_data"] = pd.DataFrame()

    # タブによる追加形式の切り替え
    tab1, tab2, tab3 = st.tabs(
        ["👤 1. キャラデータ", "📝 2. 記述問題", "🔢 3. 並び替え問題"]
    )

    # --- TAB 1: キャラデータ追加 ---
    with tab1:
        st.subheader("キャラクターマスター追加")
        if not df_all.empty:
            char_cols = [c for c in df_all.columns if c != "source_file"]
        else:
            char_cols = [
                "characterid",
                "name",
                "image",
                "nickname",
                "devil_fruit",
                "fruit_type",
                "question",
            ]

        with st.form("char_form", clear_on_submit=True):
            input_char = {}
            for col in char_cols:
                input_char[col] = st.text_input(f"{col}", key=f"char_{col}")
            input_char["type"] = "キャラデータ"

            if st.form_submit_button("キャラデータを追加"):
                new_row = pd.DataFrame([input_char])
                st.session_state["added_data"] = pd.concat(
                    [st.session_state["added_data"], new_row], ignore_index=True
                )
                st.success("キャラデータを一時保存しました！")

    # --- TAB 2: 記述問題追加 ---
    with tab2:
        st.subheader("記述式クイズ追加")
        with st.form("descriptive_form", clear_on_submit=True):
            q_text = st.text_area(
                "問題文", placeholder="例：ハイルディンの船の船員は何名か？"
            )
            a_text = st.text_input("答（正解）", placeholder="例：5名")
            exp_text = st.text_area(
                "解説・関連情報",
                placeholder="例：新巨兵海賊団の船員はハイルディン、ゲルズ、スタンセン、ロード、ゴールドバーグの5名。",
            )
            genre = st.text_input(
                "ジャンル/関連エピソード", placeholder="例：ドレスローザ編 / 麦わら大傘下"
            )

            if st.form_submit_button("記述問題を追加"):
                if q_text and a_text:
                    new_item = {
                        "type": "記述",
                        "question": q_text,
                        "answer": a_text,
                        "explanation": exp_text,
                        "genre": genre,
                    }
                    new_row = pd.DataFrame([new_item])
                    st.session_state["added_data"] = pd.concat(
                        [st.session_state["added_data"], new_row],
                        ignore_index=True,
                    )
                    st.success("記述問題を一時保存しました！")
                else:
                    st.error("問題文と答は必須項目です。")

    # --- TAB 3: 並び替え問題追加 ---
    with tab3:
        st.subheader("並び替えクイズ追加")
        with st.form("sort_form", clear_on_submit=True):
            sq_text = st.text_area(
                "問題文",
                placeholder="例：次の出来事を発生した順に並び替えよ。",
            )

            col1, col2 = st.columns(2)
            with col1:
                opt1 = st.text_input(
                    "選択肢 1 (●)", placeholder="例：アラバスタ王国脱出"
                )
                opt2 = st.text_input(
                    "選択肢 2 (△)", placeholder="例：ドラム王国脱出"
                )
            with col2:
                opt3 = st.text_input(
                    "選択肢 3 (□)", placeholder="例：ローグタウン脱出"
                )
                opt4 = st.text_input(
                    "選択肢 4 (×)", placeholder="例：空島脱出"
                )

            s_answer = st.text_input(
                "正解の順序（番号で指定）",
                placeholder="例：3214 （ローグタウン→ドラム王国→アラバスタ→空島）",
            )
            s_exp = st.text_area("解説", placeholder="時系列の補足などを記入")

            if st.form_submit_button("並び替え問題を追加"):
                if sq_text and s_answer and opt1 and opt2:
                    new_sort_item = {
                        "type": "並び替え",
                        "question": sq_text,
                        "option1": opt1,
                        "option2": opt2,
                        "option3": opt3,
                        "option4": opt4,
                        "answer": s_answer,
                        "explanation": s_exp,
                    }
                    new_row = pd.DataFrame([new_sort_item])
                    st.session_state["added_data"] = pd.concat(
                        [st.session_state["added_data"], new_row],
                        ignore_index=True,
                    )
                    st.success("並び替え問題を一時保存しました！")
                else:
                    st.error(
                        "問題文、少なくとも選択肢1・2、および正解順序を入力してください。"
                    )

    # --- 全タブ共通：保存データの確認とダウンロード ---
    if not st.session_state["added_data"].empty:
        st.write("---")
        st.subheader("📋 一時保存中の全データ一覧")
        st.dataframe(st.session_state["added_data"], use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            st.session_state["added_data"].to_excel(writer, index=False)

        col_dl, col_clr = st.columns([3, 1])
        with col_dl:
            st.download_button(
                label="📥 追加データをExcelファイルとしてダウンロード (`added_quiz_data.xlsx`)",
                data=buffer.getvalue(),
                file_name="added_quiz_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col_clr:
            if st.button("🗑️ 一時保存をクリア"):
                st.session_state["added_data"] = pd.DataFrame()
                st.rerun()

        st.caption(
            "※ダウンロードした `added_quiz_data.xlsx` をGitHubにドラッグ＆ドロップすると本番データに反映されます。"
        )
