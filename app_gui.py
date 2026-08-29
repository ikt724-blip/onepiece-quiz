import os
import io
import pandas as pd
import streamlit as st

# ------------------------------------------------------------------------------
# 初期設定 & 定数設定
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="キャラクター & 問題集マスター管理システム",
    page_icon="🏴‍☠️",
    layout="wide",
)

CHAR_MASTER_FILE = "character_master.xlsx"
QUESTION_DATA_FILE = "question_data.xlsx"
IMAGE_DIR = "images"  # 画像が格納されているディレクトリ（環境に合わせて変更してください）

# ------------------------------------------------------------------------------
# ユーティリティ関数
# ------------------------------------------------------------------------------
def get_clean_str(val):
    """NaNやNoneを空文字に変換して文字列化"""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def load_excel_data(file_path):
    """Excelファイルを読み込む（存在しない場合は空のDataFrameを返す）"""
    if os.path.exists(file_path):
        try:
            return pd.read_excel(file_path)
        except Exception as e:
            st.error(f"ファイル {file_path} の読み込みに失敗しました: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def display_question_image(row_data, width=320, is_correct_view=False):
    """
    行データから画像パス（またはURL）を取得して表示する
    """
    img_val = get_clean_str(row_data.get("Image") or row_data.get("image"))
    
    if not img_val or img_val.lower() == "none":
        st.info("🖼️ 画像指定がありません（None）。")
        return False

    # URL指定の場合
    if img_val.startswith("http://") or img_val.startswith("https://"):
        st.image(img_val, width=width, caption=f"参照URL: {img_val}")
        return True

    # ローカルファイル指定の場合
    local_path = os.path.join(IMAGE_DIR, img_val)
    if os.path.exists(local_path):
        st.image(local_path, width=width, caption=f"ファイル名: {img_val}")
        return True
    elif os.path.exists(img_val): # フルパスまたはカレントディレクトリの場合
        st.image(img_val, width=width, caption=f"ファイル名: {img_val}")
        return True
    else:
        st.warning(f"⚠️ 画像ファイルが見つかりません: {img_val}")
        return False


# ------------------------------------------------------------------------------
# Main App
# ------------------------------------------------------------------------------
def main():
    st.title("🏴‍☠️ マスターデータ閲覧・編集システム")

    # データ読み込み
    char_df = load_excel_data(CHAR_MASTER_FILE)
    question_df = load_excel_data(QUESTION_DATA_FILE)

    # メインタブの作成
    tab1, tab2 = st.tabs(["🥷 キャラクターマスター", "📝 問題集データ"])

    # ==========================================================================
    # タブ1: キャラクターマスター
    # ==========================================================================
    with tab1:
        st.subheader("🥷 キャラクターマスター 一覧")
        st.caption("💡 表の中の**任意の行をクリック**すると、直下に該当キャラクターの画像が表示されます。")

        if char_df.empty:
            st.warning(f"ファイル `{CHAR_MASTER_FILE}` が見つからないか、データが空です。")
        else:
            # --- 1. クリック選択付きデータフレーム ---
            event_char = st.dataframe(
                char_df,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                key="char_table_select",
            )

            # --- 2. 選択された行の画像表示エリア ---
            st.markdown("---")
            selected_char_rows = event_char.selection.get("rows", [])

            if selected_char_rows:
                selected_idx = selected_char_rows[0]
                selected_row = char_df.iloc[selected_idx]

                c_name = get_clean_str(selected_row.get("name")) or "名称未設定"
                c_id = get_clean_str(selected_row.get("characterid"))
                
                st.markdown(f"### 🖼️ 選択中のキャラクター: **{c_name}** `({c_id})`")
                
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    display_question_image(selected_row, width=300)
                with col_info:
                    st.markdown(f"**異名 / 通称:** {get_clean_str(selected_row.get('nickname')) or 'なし'}")
                    st.markdown(f"**悪魔の実:** {get_clean_str(selected_row.get('devil_fruit')) or 'なし'}")
                    st.markdown(f"**系統:** {get_clean_str(selected_row.get('fruit_type')) or 'なし'}")
            else:
                st.info("👆 上の表から行をクリックすると、ここにキャラクターの画像と詳細情報が表示されます。")

            # --- 3. 編集用アコーディオン ---
            with st.expander("✏️ データの編集・セル書き換え・保存はこちら"):
                st.caption("※ セルを直接編集後、下のダウンロードボタンからExcel形式で保存できます。")
                edited_char_df = st.data_editor(
                    char_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="editor_char_data",
                )
                
                # Excel出力準備
                buffer_char = io.BytesIO()
                with pd.ExcelWriter(buffer_char, engine="openpyxl") as writer:
                    edited_char_df.to_excel(writer, index=False)

                st.download_button(
                    label="📥 編集後のデータをダウンロード (`character_master.xlsx`)",
                    data=buffer_char.getvalue(),
                    file_name="character_master.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    # ==========================================================================
    # タブ2: 問題集データ
    # ==========================================================================
    with tab2:
        st.subheader("📝 問題集データ 一覧")
        st.caption("💡 表の中の**任意の行をクリック**すると、直下に問題に関連する画像が表示されます。")

        if question_df.empty:
            st.warning(f"ファイル `{QUESTION_DATA_FILE}` が見つからないか、データが空です。")
        else:
            # --- 1. クリック選択付きデータフレーム ---
            event_q = st.dataframe(
                question_df,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                key="q_table_select",
            )

            # --- 2. 選択された行の画像表示エリア ---
            st.markdown("---")
            selected_q_rows = event_q.selection.get("rows", [])

            if selected_q_rows:
                selected_idx = selected_q_rows[0]
                selected_row = question_df.iloc[selected_idx]

                q_id = get_clean_str(selected_row.get("question_id") or selected_row.get("id"))
                st.markdown(f"### 🖼️ 選択中の問題: **{q_id}**")
                
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    display_question_image(selected_row, width=320)
                with col_info:
                    st.markdown(f"**問題文:**\n{get_clean_str(selected_row.get('question_text'))}")
                    st.markdown(f"**正解:** {get_clean_str(selected_row.get('answer'))}")
            else:
                st.info("👆 上の表から行をクリックすると、ここに問題画像が表示されます。")

            # --- 3. 編集用アコーディオン ---
            with st.expander("✏️ データの編集・セル書き換え・保存はこちら"):
                edited_q_df = st.data_editor(
                    question_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="editor_q_data",
                )
                
                buffer_q = io.BytesIO()
                with pd.ExcelWriter(buffer_q, engine="openpyxl") as writer:
                    edited_q_df.to_excel(writer, index=False)

                st.download_button(
                    label="📥 編集後のデータをダウンロード (`question_data.xlsx`)",
                    data=buffer_q.getvalue(),
                    file_name="question_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

if __name__ == "__main__":
    main()
