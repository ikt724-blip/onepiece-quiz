import glob
import io
import os
import random
import re
import time
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


# 正解判定共通ロジック
def check_answer(user_input, correct_ans):
    u_clean = str(user_input).strip()
    correct_ans = str(correct_ans).strip()
    if not u_clean:
        return False
    if correct_ans == u_clean:
        return True
    if "、" in correct_ans or "," in correct_ans:
        targets = [
            t.strip() for t in re.split(r"[、,]", correct_ans) if t.strip()
        ]
        user_parts = [
            u.strip() for u in re.split(r"[、,,\s]", u_clean) if u.strip()
        ]
        if set(targets) == set(user_parts):
            return True
    return False


# --- ページ基本設定 ---
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策", page_icon="🏴‍☠️", layout="wide"
)

# --- サイドバーナビゲーション ---
with st.sidebar:
    st.header("🏴‍☠️ ナビセンター")
    selected = option_menu(
        menu_title=None,
        options=[
            "ホーム",
            "📖 練習モード",
            "🏆 本番模試（50問/60分）",
            "🔥 苦手克服",
            "🔍 AI検索モード",
            "➕ データ追加",
        ],
        icons=[
            "house",
            "book",
            "trophy",
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

# --- 2. 練習モード ---
elif selected == "📖 練習モード":
    st.subheader("📖 練習モード")

    if df_all.empty:
        st.warning("出題できるデータが見つかりません。")
    else:
        if "practice_started" not in st.session_state:
            st.session_state.practice_started = False
        if "p_curr_idx" not in st.session_state:
            st.session_state.p_curr_idx = 0
        if "p_quiz_list" not in st.session_state:
            st.session_state.p_quiz_list = []
        if "p_score" not in st.session_state:
            st.session_state.p_score = 0
        if "p_user_answers" not in st.session_state:
            st.session_state.p_user_answers = []

        if not st.session_state.practice_started:
            st.success(
                f"全 {len(df_all)} 問の中から自由に出題条件を設定できます。"
            )

            col1, col2 = st.columns(2)
            with col1:
                num_q = st.number_input(
                    "出題数を選択",
                    min_value=1,
                    max_value=min(len(df_all), 100),
                    value=min(len(df_all), 10),
                )
            with col2:
                q_type_filter = st.selectbox(
                    "問題タイプ", ["すべて", "記述問題", "並び替え問題", "キャラマスター"]
                )

            if st.button("🚀 練習を開始する", use_container_width=True):
                target_df = df_all.copy()
                if q_type_filter == "記述問題" and "type" in target_df.columns:
                    target_df = target_df[target_df["type"] == "記述"]
                elif (
                    q_type_filter == "並び替え問題" and "type" in target_df.columns
                ):
                    target_df = target_df[target_df["type"] == "並び替え"]
                elif (
                    q_type_filter == "キャラマスター"
                    and "type" in target_df.columns
                ):
                    target_df = target_df[target_df["type"] == "キャラデータ"]

                if target_df.empty:
                    target_df = df_all.copy()

                shuffled = target_df.sample(
                    n=min(num_q, len(target_df))
                ).reset_index(drop=True)
                st.session_state.p_quiz_list = shuffled.to_dict("records")
                st.session_state.p_curr_idx = 0
                st.session_state.p_score = 0
                st.session_state.p_user_answers = []
                st.session_state.practice_started = True
                st.rerun()

        else:
            total_q = len(st.session_state.p_quiz_list)
            curr_idx = st.session_state.p_curr_idx

            if curr_idx >= total_q:
                st.balloons()
                st.markdown(
                    f"## 🎉 練習終了！\n### 結果: **{total_q}** 問中 **{st.session_state.p_score}** 問正解！"
                )
                res_df = pd.DataFrame(st.session_state.p_user_answers)
                if not res_df.empty:
                    st.dataframe(res_df, use_container_width=True)

                if st.button("🔄 もう一度練習する"):
                    st.session_state.practice_started = False
                    st.rerun()
            else:
                q = st.session_state.p_quiz_list[curr_idx]
                st.progress((curr_idx) / total_q)
                st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")

                question_text = (
                    q.get("question")
                    or q.get("問題")
                    or (f"「{q.get('name')}」の悪魔の日は何か？" if q.get("name") else "")
                )
                st.info(f"**【問題】**\n{question_text}")

                img_name = str(q.get("image", ""))
                if img_name and img_name != "nan":
                    imgPath = (
                        img_name
                        if os.path.exists(img_name)
                        else os.path.join("images", img_name)
                    )
                    if os.path.exists(imgPath):
                        st.image(imgPath, width=300)

                is_sort = (
                    q.get("type") == "並び替え"
                    or "option1" in q
                    and pd.notna(q.get("option1"))
                )
                if is_sort:
                    st.write("【選択肢】")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"1. {q.get('option1', '')}")
                        st.write(f"2. {q.get('option2', '')}")
                    with c2:
                        st.write(f"3. {q.get('option3', '')}")
                        st.write(f"4. {q.get('option4', '')}")

                correct_ans = str(
                    q.get("answer")
                    or q.get("解答")
                    or q.get("devil_fruit")
                    or ""
                ).strip()

                with st.form(f"practice_form_{curr_idx}"):
                    user_input = st.text_input(
                        "解答を入力",
                        placeholder="（並び替えは『2431』のように番号で入力）"
                        if is_sort
                        else "ここに解答を記入",
                    )
                    sub_c1, sub_c2 = st.columns(2)
                    with sub_c1:
                        submitted = st.form_submit_button(
                            "回答する", use_container_width=True
                        )
                    with sub_c2:
                        passed = st.form_submit_button(
                            "パス", use_container_width=True
                        )

                if submitted:
                    is_correct = check_answer(user_input, correct_ans)
                    if is_correct:
                        st.success("⭕ 正解！")
                        st.session_state.p_score += 1
                    else:
                        st.error(f"❌ 不正解... 正解は: **{correct_ans}**")

                    exp = q.get("explanation") or q.get("解説") or ""
                    if pd.notna(exp) and str(exp).strip():
                        st.caption(f"💡 【解説】: {exp}")

                    st.session_state.p_user_answers.append(
                        {
                            "問題": question_text,
                            "あなたの解答": user_input,
                            "正解": correct_ans,
                            "判定": "⭕ 正解" if is_correct else "❌ 不正解",
                        }
                    )
                    st.session_state.p_curr_idx += 1
                    st.button("次の問題へ ➡")

                elif passed:
                    st.session_state.p_curr_idx += 1
                    st.rerun()

                if st.button("練習を中断する"):
                    st.session_state.practice_started = False
                    st.rerun()

# --- 3. 本番模試（50問 / 60分制限） ---
elif selected == "🏆 本番模試（50問/60分）":
    st.subheader("🏆 ナレッジキング模擬試験（50問 / 制限時間60分）")

    if df_all.empty:
        st.warning("出題できるデータが見つかりません。")
    else:
        if "exam_started" not in st.session_state:
            st.session_state.exam_started = False
        if "exam_start_time" not in st.session_state:
            st.session_state.exam_start_time = 0
        if "e_curr_idx" not in st.session_state:
            st.session_state.e_curr_idx = 0
        if "e_quiz_list" not in st.session_state:
            st.session_state.e_quiz_list = []
        if "e_user_answers" not in st.session_state:
            st.session_state.e_user_answers = {}

        if not st.session_state.exam_started:
            st.info(
                "全データからランダムで **50問** 出題されます。制限時間は **60分** です。"
            )
            st.write(
                "※本番同様、テスト挑戦中は途中で正解が表示されません。最後に総合結果が出力されます。"
            )

            if st.button("🔥 模試を開始する（タイマースタート）", use_container_width=True):
                shuffled = df_all.sample(n=min(50, len(df_all))).reset_index(
                    drop=True
                )
                st.session_state.e_quiz_list = shuffled.to_dict("records")
                st.session_state.e_curr_idx = 0
                st.session_state.e_user_answers = {}
                st.session_state.exam_start_time = time.time()
                st.session_state.exam_started = True
                st.rerun()

        else:
            # 経過時間・残り時間計算
            elapsed_time = int(time.time() - st.session_state.exam_start_time)
            total_time_limit = 60 * 60  # 60分
            remaining_time = max(0, total_time_limit - elapsed_time)

            mins, secs = divmod(remaining_time, 60)

            # タイマー表示（上部固定風）
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1:
                st.progress(
                    (st.session_state.e_curr_idx)
                    / len(st.session_state.e_quiz_list)
                )
            with col_t2:
                if remaining_time > 0:
                    st.error(f"⏱️ 残り時間: **{mins:02d}分 {secs:02d}秒**")
                else:
                    st.error("⏰ タイムアップ！")

            total_q = len(st.session_state.e_quiz_list)
            curr_idx = st.session_state.e_curr_idx

            # タイムアップまたは全問終了時
            if remaining_time <= 0 or curr_idx >= total_q:
                st.balloons()
                st.markdown("## 🏁 模試終了！ 採点結果")

                # 採点ロジック
                score = 0
                summary_data = []
                for idx, q_item in enumerate(st.session_state.e_quiz_list):
                    u_ans = st.session_state.e_user_answers.get(idx, "")
                    c_ans = str(
                        q_item.get("answer")
                        or q_item.get("解答")
                        or q_item.get("devil_fruit")
                        or ""
                    ).strip()
                    is_c = check_answer(u_ans, c_ans)
                    if is_c:
                        score += 1

                    q_txt = (
                        q_item.get("question")
                        or q_item.get("問題")
                        or q_item.get("name")
                    )
                    summary_data.append(
                        {
                            "問": idx + 1,
                            "問題文": q_txt,
                            "あなたの解答": u_ans,
                            "正解": c_ans,
                            "判定": "⭕ 正解" if is_c else "❌ 不正解",
                        }
                    )

                st.markdown(
                    f"### 最終得点: **{score}** / {total_q} 問 (正答率: {int(score/total_q*100)}%)"
                )
                st.write("---")
                st.subheader("📋 解答一覧と詳細")
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

                if st.button("🔄 もう一度模試を受ける"):
                    st.session_state.exam_started = False
                    st.rerun()

            else:
                q = st.session_state.e_quiz_list[curr_idx]
                st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")

                question_text = (
                    q.get("question")
                    or q.get("問題")
                    or (f"「{q.get('name')}」の悪魔の日は何か？" if q.get("name") else "")
                )
                st.info(f"**【問題】**\n{question_text}")

                img_name = str(q.get("image", ""))
                if img_name and img_name != "nan":
                    imgPath = (
                        img_name
                        if os.path.exists(img_name)
                        else os.path.join("images", img_name)
                    )
                    if os.path.exists(imgPath):
                        st.image(imgPath, width=300)

                is_sort = (
                    q.get("type") == "並び替え"
                    or "option1" in q
                    and pd.notna(q.get("option1"))
                )
                if is_sort:
                    st.write("【選択肢】")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"1. {q.get('option1', '')}")
                        st.write(f"2. {q.get('option2', '')}")
                    with c2:
                        st.write(f"3. {q.get('option3', '')}")
                        st.write(f"4. {q.get('option4', '')}")

                prev_val = st.session_state.e_user_answers.get(curr_idx, "")
                with st.form(f"exam_form_{curr_idx}"):
                    user_input = st.text_input(
                        "解答を入力してください", value=prev_val
                    )
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        sub_next = st.form_submit_button(
                            "回答して次の問題へ ➡", use_container_width=True
                        )
                    with col_b2:
                        sub_skip = st.form_submit_button(
                            "スキップ", use_container_width=True
                        )

                if sub_next:
                    st.session_state.e_user_answers[curr_idx] = (
                        user_input.strip()
                    )
                    st.session_state.e_curr_idx += 1
                    st.rerun()
                elif sub_skip:
                    st.session_state.e_curr_idx += 1
                    st.rerun()

                if st.button("模試を中断して提出する"):
                    st.session_state.e_curr_idx = total_q
                    st.rerun()

# --- 4. 苦手克服 ---
elif selected == "🔥 苦手克服":
    st.subheader("🔥 苦手克服モード")
    st.info("間違えた問題やチェックした問題を重点的に復習できます。")

# --- 5. AI検索モード ---
elif selected == "🔍 AI検索モード":
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

# --- 6. データ追加 ---
elif selected == "➕ データ追加":
    st.title("➕ データ追加")
    st.caption(
        "問題のタイプに合わせて専用フォームから登録・Excel出力ができます。"
    )
    st.write("---")

    if "added_data" not in st.session_state:
        st.session_state["added_data"] = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(
        ["👤 1. キャラデータ", "📝 2. 記述問題", "🔢 3. 並び替え問題"]
    )

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

    with tab2:
        st.subheader("記述式クイズ追加")

        num_answers = st.selectbox(
            "解答（正解）の項目数を選択",
            options=[1, 2, 3, 4, 5],
            index=0,
            help="四皇をすべて答える問題など、複数解答がある場合は項目数を変更してください。",
        )

        with st.form("descriptive_form", clear_on_submit=True):
            q_text = st.text_area(
                "問題文",
                placeholder="例：現在の四皇（新四皇）の名称をすべて答えろ。",
            )

            ans_inputs = []
            cols = st.columns(min(num_answers, 3))
            for i in range(num_answers):
                col_target = cols[i % 3]
                with col_target:
                    ans_val = st.text_input(
                        f"正解 {i+1}",
                        placeholder=f"例：正解{i+1}",
                        key=f"ans_input_{i}",
                    )
                    ans_inputs.append(ans_val)

            exp_text = st.text_area(
                "解説・関連情報",
                placeholder="例：ルフィ、バギー、シャンクス、ティーチの4名。",
            )
            genre = st.text_input(
                "ジャンル/関連エピソード", placeholder="例：ワノ国編後 / 懸賞金"
            )

            if st.form_submit_button("記述問題を追加"):
                valid_answers = [
                    a.strip() for a in ans_inputs if a and a.strip()
                ]
                if q_text and valid_answers:
                    combined_answer = "、".join(valid_answers)
                    new_item = {
                        "type": "記述",
                        "question": q_text,
                        "answer": combined_answer,
                        "answer_count": len(valid_answers),
                        "explanation": exp_text,
                        "genre": genre,
                    }
                    for idx, a_val in enumerate(ans_inputs):
                        new_item[f"answer_{idx+1}"] = a_val

                    new_row = pd.DataFrame([new_item])
                    st.session_state["added_data"] = pd.concat(
                        [st.session_state["added_data"], new_row],
                        ignore_index=True,
                    )
                    st.success(
                        f"記述問題（解答{len(valid_answers)}件）を一時保存しました！"
                    )
                else:
                    st.error("問題文と少なくとも1つの正解を入力してください。")

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
            if st.button("🗑️ 一时保存をクリア"):
                st.session_state["added_data"] = pd.DataFrame()
                st.rerun()

        st.caption(
            "※ダウンロードした `added_quiz_data.xlsx` をGitHubにドラッグ＆ドロップすると本番データに反映されます。"
        )
