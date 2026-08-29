import os
import io
import random
import pandas as pd
import streamlit as st

# ------------------------------------------------------------------------------
# 初期設定 & 定数設定
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策システム",
    page_icon="🏴‍☠️",
    layout="wide",
)

CHAR_MASTER_FILE = "character_master.xlsx"
QUESTION_DATA_FILE = "question_data.xlsx"
IMAGE_DIR = "images"

# Session State の初期化
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "current_q_idx" not in st.session_state:
    st.session_state.current_q_idx = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []

# ------------------------------------------------------------------------------
# ユーティリティ関数
# ------------------------------------------------------------------------------
def get_clean_str(val):
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def load_excel_data(file_path):
    if os.path.exists(file_path):
        try:
            return pd.read_excel(file_path)
        except Exception as e:
            st.error(f"ファイル {file_path} の読み込みに失敗しました: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_excel_data(df, file_path):
    try:
        df.to_excel(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"ファイルの保存に失敗しました: {e}")
        return False

def display_question_image(row_data, width=320):
    img_val = get_clean_str(row_data.get("Image") or row_data.get("image"))
    if not img_val or img_val.lower() == "none":
        st.info("🖼️ 画像指定がありません（None）。")
        return False

    if img_val.startswith("http://") or img_val.startswith("https://"):
        st.image(img_val, width=width, caption=f"参照URL: {img_val}")
        return True

    local_path = os.path.join(IMAGE_DIR, img_val)
    if os.path.exists(local_path):
        st.image(local_path, width=width, caption=f"ファイル名: {img_val}")
        return True
    elif os.path.exists(img_val):
        st.image(img_val, width=width, caption=f"ファイル名: {img_val}")
        return True
    else:
        st.warning(f"⚠️ 画像ファイルが見つかりません: {img_val}")
        return False

# ------------------------------------------------------------------------------
# メインアプリケーション
# ------------------------------------------------------------------------------
def main():
    st.title("🏴‍☠️ ONE PIECE ナレッジキング対策システム")

    char_df = load_excel_data(CHAR_MASTER_FILE)
    question_df = load_excel_data(QUESTION_DATA_FILE)

    # サイドメニューでモード切り替え
    st.sidebar.title("📌 メニュー")
    mode = st.sidebar.radio(
        "モードを選択してください",
        ["🎲 ランダム出題（練習）", "📝 模擬試験（テスト）", "⚙️ マスターデータ閲覧・編集"]
    )

    # ==========================================================================
    # モード1: ランダム出題（練習モード）
    # ==========================================================================
    if mode == "🎲 ランダム出題（練習）":
        st.header("🎲 ランダム出題（練習モード）")

        if question_df.empty:
            st.warning("問題集データが読み込めません。")
            return

        if st.button("🔄 次の問題をセット") or "random_row" not in st.session_state:
            st.session_state.random_row = question_df.sample(n=1).iloc[0]
            st.session_state.show_ans = False

        q_row = st.session_state.random_row

        st.subheader(f"問題: {get_clean_str(q_row.get('question_text') or q_row.get('question'))}")
        display_question_image(q_row, width=400)

        user_input = st.text_input("解答を入力してください:", key="practice_input")

        if st.button("解答を確認する"):
            st.session_state.show_ans = True

        if st.session_state.get("show_ans", False):
            correct_ans = get_clean_str(q_row.get("answer"))
            if user_input.strip() == correct_ans:
                st.success(f"🎉 正解！\n**正解:** {correct_ans}")
            else:
                st.error(f"❌ 不正解...\n**あなたの解答:** {user_input}\n**正解:** {correct_ans}")
            
            exp = get_clean_str(q_row.get("explanation"))
            if exp:
                st.info(f"💡 **解説:** {exp}")

    # ==========================================================================
    # モード2: 模擬試験（テストモード）
    # ==========================================================================
    elif mode == "📝 模擬試験（テスト）":
        st.header("📝 模擬試験（テストモード）")

        if question_df.empty:
            st.warning("問題集データが読み込めません。")
            return

        # テスト開始前画面
        if not st.session_state.quiz_started:
            num_q = st.number_input("出題数を指定してください", min_value=1, max_value=len(question_df), value=min(10, len(question_df)))
            if st.button("🚀 模擬試験を開始する"):
                st.session_state.quiz_questions = question_df.sample(n=num_q).to_dict("records")
                st.session_state.quiz_started = True
                st.session_state.current_q_idx = 0
                st.session_state.user_answers = {}
                st.rerun()

        # テスト実行画面
        else:
            q_list = st.session_state.quiz_questions
            c_idx = st.session_state.current_q_idx
            q_count = len(q_list)

            if c_idx < q_count:
                q_row = q_list[c_idx]
                st.progress((c_idx + 1) / q_count)
                st.subheader(f"第 {c_idx + 1} 問 / 全 {q_count} 問")
                st.write(get_clean_str(q_row.get("question_text") or q_row.get("question")))

                display_question_image(q_row, width=350)

                ans_key = f"quiz_ans_{c_idx}"
                current_val = st.session_state.user_answers.get(c_idx, "")
                user_ans = st.text_input("解答:", value=current_val, key=ans_key)
                st.session_state.user_answers[c_idx] = user_ans

                col_prev, col_next = st.columns([1, 1])
                with col_prev:
                    if c_idx > 0 and st.button("◀ 前の問題へ"):
                        st.session_state.current_q_idx -= 1
                        st.rerun()
                with col_next:
                    if c_idx < q_count - 1:
                        if st.button("次の問題へ ▶"):
                            st.session_state.current_q_idx += 1
                            st.rerun()
                    else:
                        if st.button("🏁 採点して結果を見る"):
                            st.session_state.current_q_idx = q_count
                            st.rerun()

            # テスト結果発表画面
            else:
                st.subheader("📊 採点結果")
                score = 0
                for idx, q_row in enumerate(q_list):
                    u_ans = get_clean_str(st.session_state.user_answers.get(idx, ""))
                    c_ans = get_clean_str(q_row.get("answer"))
                    is_correct = (u_ans == c_ans)
                    if is_correct:
                        score += 1

                    status = "✅ 正解" if is_correct else "❌ 不正解"
                    with st.expander(f"問 {idx + 1}: {status}"):
                        st.write(f"**問題:** {get_clean_str(q_row.get('question_text') or q_row.get('question'))}")
                        st.write(f"**あなたの解答:** {u_ans}")
                        st.write(f"**正解:** {c_ans}")
                        exp = get_clean_str(q_row.get("explanation"))
                        if exp:
                            st.write(f"**解説:** {exp}")

                st.markdown(f"### **最終スコア: {score} / {q_count} 点** (正解率: {int(score/q_count*100)}%)")

                if st.button("🔄 もう一度模擬試験を受ける"):
                    st.session_state.quiz_started = False
                    st.rerun()

    # ==========================================================================
    # モード3: マスターデータ閲覧・編集（クリックで画像表示）
    # ==========================================================================
    elif mode == "⚙️ マスターデータ閲覧・編集":
        tab1, tab2 = st.tabs(["👥 キャラクターマスター", "📝 問題集データ"])

        # ── タブ1: キャラクターマスター ──
        with tab1:
            st.subheader("👥 キャラクターマスター 一覧")
            st.caption("💡 **表の中の行をクリック**すると、直下に該当キャラクターの画像が表示されます。")

            if char_df.empty:
                st.warning(f"ファイル `{CHAR_MASTER_FILE}` が見つからないか、データが空です。")
            else:
                # 行クリック検知付きデータフレーム
                event_char = st.dataframe(
                    char_df,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="char_table_select",
                )

                # 行選択時の画像表示エリア
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
                        st.markdown(f"**ソースファイル:** {get_clean_str(selected_row.get('source_file')) or 'なし'}")
                else:
                    st.info("👆 上の表から行をクリックすると、ここにキャラクターの画像と詳細が表示されます。")

                st.markdown("---")

                # データ編集 & 追加
                col_edit, col_add = st.columns([2, 1])

                with col_edit:
                    with st.expander("✏️ セルの直接編集・書き換え"):
                        edited_char_df = st.data_editor(
                            char_df,
                            num_rows="dynamic",
                            use_container_width=True,
                            key="editor_char_data",
                        )
                        
                        if st.button("💾 キャラクターデータを上書き保存", key="save_char_btn"):
                            if save_excel_data(edited_char_df, CHAR_MASTER_FILE):
                                st.success("キャラクターデータを保存しました！")
                                st.rerun()

                with col_add:
                    with st.expander("➕ 新規キャラクター追加"):
                        with st.form("add_char_form"):
                            new_id = st.text_input("characterid (例: CH00175)")
                            new_name = st.text_input("name (名前)")
                            new_img = st.text_input("image (画像ファイル名/URL)")
                            new_nick = st.text_input("nickname (異名)")
                            new_fruit = st.text_input("devil_fruit (悪魔の実)")
                            new_ftype = st.text_input("fruit_type (系統)")
                            
                            submitted = st.form_submit_button("追加する")
                            if submitted:
                                new_row = {
                                    "source_file": "character_master.xlsx",
                                    "characterid": new_id,
                                    "name": new_name,
                                    "image": new_img,
                                    "nickname": new_nick,
                                    "devil_fruit": new_fruit,
                                    "fruit_type": new_ftype
                                }
                                updated_df = pd.concat([char_df, pd.DataFrame([new_row])], ignore_index=True)
                                if save_excel_data(updated_df, CHAR_MASTER_FILE):
                                    st.success(f"「{new_name}」を追加しました！")
                                    st.rerun()

        # ── タブ2: 問題集データ ──
        with tab2:
            st.subheader("📝 問題集データ 一覧")
            st.caption("💡 **表の中の行をクリック**すると、直下に問題に関連する画像が表示されます。")

            if question_df.empty:
                st.warning(f"ファイル `{QUESTION_DATA_FILE}` が見つからないか、データが空です。")
            else:
                event_q = st.dataframe(
                    question_df,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="q_table_select",
                )

                st.markdown("---")
                selected_q_rows = event_q.selection.get("rows", [])

                if selected_q_rows:
                    selected_idx = selected_q_rows[0]
                    selected_row = question_df.iloc[selected_idx]

                    q_id = get_clean_str(selected_row.get("question_id") or selected_row.get("id") or f"ROW-{selected_idx+1}")
                    st.markdown(f"### 🖼️ 選択中の問題 ID: **{q_id}**")
                    
                    col_img, col_info = st.columns([1, 2])
                    with col_img:
                        display_question_image(selected_row, width=320)
                    with col_info:
                        st.markdown(f"**問題文:**\n{get_clean_str(selected_row.get('question_text') or selected_row.get('question'))}")
                        st.markdown(f"**正解:** {get_clean_str(selected_row.get('answer'))}")
                        st.markdown(f"**解説:** {get_clean_str(selected_row.get('explanation'))}")
                else:
                    st.info("👆 上の表から行をクリックすると、ここに問題画像が表示されます。")

                st.markdown("---")

                col_q_edit, col_q_add = st.columns([2, 1])

                with col_q_edit:
                    with st.expander("✏️ セルの直接編集・書き換え"):
                        edited_q_df = st.data_editor(
                            question_df,
                            num_rows="dynamic",
                            use_container_width=True,
                            key="editor_q_data",
                        )
                        
                        if st.button("💾 問題集データを上書き保存", key="save_q_btn"):
                            if save_excel_data(edited_q_df, QUESTION_DATA_FILE):
                                st.success("問題集データを保存しました！")
                                st.rerun()

                with col_q_add:
                    with st.expander("➕ 新規問題の追加"):
                        with st.form("add_question_form"):
                            q_id_input = st.text_input("question_id (問題ID)")
                            q_text_input = st.text_area("question_text (問題文)")
                            q_ans_input = st.text_input("answer (正解)")
                            q_img_input = st.text_input("image (画像名/URL)")
                            q_exp_input = st.text_area("explanation (解説)")

                            q_submitted = st.form_submit_button("問題を追加する")
                            if q_submitted:
                                new_q_row = {
                                    "question_id": q_id_input,
                                    "question_text": q_text_input,
                                    "answer": q_ans_input,
                                    "image": q_img_input,
                                    "explanation": q_exp_input
                                }
                                updated_q_df = pd.concat([question_df, pd.DataFrame([new_q_row])], ignore_index=True)
                                if save_excel_data(updated_q_df, QUESTION_DATA_FILE):
                                    st.success("新しい問題を追加しました！")
                                    st.rerun()

if __name__ == "__main__":
    main()
