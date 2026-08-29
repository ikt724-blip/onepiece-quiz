import glob
import io
import math
import os
import random
import re
import time
import base64
import pandas as pd
import qrcode
import streamlit as st
from PIL import Image
from streamlit_option_menu import option_menu


# --- データ読み込み用共通関数 ---
@st.cache_data
def load_all_data():
    """リポジトリ内の全Excelファイルを統合して読み込む"""
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


# 有効文字列判定ヘルパー
def get_clean_str(val):
    """NaNやNone、空文字を排除して正しい文字列を返す"""
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ["nan", "none", "<na>"]:
        return ""
    return s


# 画像保存用ヘルパー関数
def save_uploaded_image(uploaded_file):
    """アップロードされた画像を ./images/ フォルダに保存してファイル名を返す"""
    if uploaded_file is None:
        return ""
    os.makedirs("images", exist_ok=True)
    file_path = os.path.join("images", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return uploaded_file.name


# 画像表示ヘルパー関数（問題用・正解用切り替え対応）
def display_question_image(q_data, width=350, caption=None, is_correct_view=False):
    """画像パスを探して表示する関数（is_correct_view=True で正解画像の表示を優先）"""
    img_name = ""
    if is_correct_view:
        img_name = get_clean_str(q_data.get("correct_image") or q_data.get("正解画像"))

    if not img_name:
        img_name = get_clean_str(q_data.get("image") or q_data.get("画像"))

    if img_name:
        imgPath = (
            img_name
            if os.path.exists(img_name)
            else os.path.join("images", img_name)
        )
        if os.path.exists(imgPath):
            st.image(imgPath, width=width, caption=caption or ("【正解画像】" if is_correct_view else None))
            return True
    return False


# 正解リスト抽出ヘルパー
def get_correct_answers_list(q, correct_ans_str):
    """問題データから正解の要素リストを取得する"""
    answers = []
    for i in range(1, 10):
        val = get_clean_str(q.get(f"answer_{i}"))
        if val:
            answers.append(val)
            
    if not answers and correct_ans_str:
        if "、" in correct_ans_str or "," in correct_ans_str:
            answers = [
                t.strip() for t in re.split(r"[、,]", correct_ans_str) if t.strip()
            ]
        else:
            answers = [correct_ans_str.strip()]
            
    return answers


# 正解判定共通ロジック (順不同対応)
def check_answers_multi(user_inputs, correct_answers):
    """複数入力された回答と正解リストを順不同で照合"""
    user_clean = [str(u).strip() for u in user_inputs if str(u).strip()]
    correct_clean = [str(c).strip() for c in correct_answers if str(c).strip()]

    if len(user_clean) != len(correct_clean):
        return False

    return set(user_clean) == set(correct_clean)


# キャラマスターデータから問題文と正解を確定させるロジック
def format_question_and_answer(q):
    raw_question = get_clean_str(
        q.get("question") or q.get("問題") or q.get("Question")
    )
    name = get_clean_str(
        q.get("name") or q.get("名前") or q.get("キャラ名") or q.get("Name")
    )
    image = get_clean_str(q.get("image") or q.get("画像"))
    devil_fruit = get_clean_str(
        q.get("devil_fruit") or q.get("悪魔の実") or q.get("能力")
    )
    affiliation = get_clean_str(
        q.get("affiliation") or q.get("所属") or q.get("組織")
    )
    nickname = get_clean_str(
        q.get("nickname") or q.get("異名") or q.get("通り名")
    )

    if raw_question:
        ans = get_clean_str(
            q.get("answer")
            or q.get("解答")
            or q.get("正解")
            or devil_fruit
            or name
        )
        return raw_question, ans

    if image and name:
        return "このキャラクターの名前は？", name

    if devil_fruit and name:
        return f"「{name}」が食べた悪魔の実の名称は？", devil_fruit

    if affiliation and name:
        return f"「{name}」の主な所属（組織・海賊団など）は？", affiliation

    if nickname and name:
        return f"「{name}」の異名（通り名）は？", nickname

    if name:
        return "このキャラクターの名前は？", name

    return "このキャラクターの名前は？", name


# --- ページ基本設定 ---
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策", page_icon="🏴‍☠️", layout="wide"
)

# 画面切り替え用の状態初期化
if "current_nav" not in st.session_state:
    st.session_state["current_nav"] = "ホーム"

menu_options = [
    "ホーム",
    "📖 練習モード",
    "🏆 本番模試（50問/60分）",
    "🔥 苦手克服",
    "🔍 AI検索モード",
    "➕ データ追加・編集",
]

# --- サイドバーナビゲーション ---
with st.sidebar:
    st.header("🏴‍☠️ ナビセンター")

    def_idx = (
        menu_options.index(st.session_state["current_nav"])
        if st.session_state["current_nav"] in menu_options
        else 0
    )

    selected = option_menu(
        menu_title=None,
        options=menu_options,
        icons=[
            "house",
            "book",
            "trophy",
            "exclamation-triangle",
            "search",
            "plus-circle",
        ],
        default_index=def_idx,
        key="nav_menu",
    )
    st.session_state["current_nav"] = selected

# 全データ取得
df_all = load_all_data()

# --- 1. ホーム画面 ---
if selected == "ホーム":
    all_imgs = (
        glob.glob("images/*.png")
        + glob.glob("images/*.jpg")
        + glob.glob("images/*.jpeg")
        + glob.glob("*.png")
        + glob.glob("*.jpg")
    )

    grid_imgs_html = ""
    if all_imgs:
        sample_imgs = [random.choice(all_imgs) for _ in range(60)]
        for img_path in sample_imgs:
            try:
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    ext = img_path.split(".")[-1].lower()
                    mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                    grid_imgs_html += f'<img src="data:{mime};base64,{b64}" class="bg-tile" />'
            except Exception:
                continue

    banner_html = f"""
    <style>
    .wt100-container {{
        position: relative;
        width: 100%;
        height: 420px;
        border-radius: 16px;
        overflow: hidden;
        border: 2px solid #333;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        background-color: #0d0d0d;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    
    .mosaic-bg {{
        position: absolute;
        top: -50%;
        left: 0;
        width: 100%;
        height: 200%;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(85px, 1fr));
        grid-auto-rows: 85px;
        gap: 3px;
        opacity: 0.85;
        animation: scroll-down 25s linear infinite;
    }}

    @keyframes scroll-down {{
        0% {{
            transform: translateY(0);
        }}
        100% {{
            transform: translateY(25%);
        }}
    }}
    
    .bg-tile {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}

    .center-overlay {{
        position: relative;
        z-index: 2;
        background: transparent;
        backdrop-filter: blur(2px);
        padding: 35px 50px;
        border-radius: 16px;
        border: 3px solid #ffcc00;
        text-align: center;
        box-shadow: 0 0 25px rgba(255, 204, 0, 0.5), inset 0 0 15px rgba(0, 0, 0, 0.5);
        max-width: 85%;
    }}
    
    .center-overlay h1 {{
        margin: 0 0 10px 0;
        font-size: 2.5rem;
        color: #ffffff;
        font-weight: 900;
        text-shadow: 3px 3px 6px #000000, -2px -2px 4px #000000, 2px -2px 4px #000000, -2px 2px 4px #000000;
        letter-spacing: 2px;
    }}
    
    .center-overlay p {{
        margin: 0;
        color: #ffcc00;
        font-size: 1.25rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px #000000, -1px -1px 2px #000000;
        letter-spacing: 3px;
    }}
    </style>

    <div class="wt100-container">
        <div class="mosaic-bg">
            {grid_imgs_html if grid_imgs_html else '<div style="grid-column: 1/-1; text-align:center; color:#888; padding-top:180px;">（画像を追加すると背景にモザイク表示されます）</div>'}
        </div>
        <div class="center-overlay">
            <h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1>
            <p>― 最強のデータベースを脳に刻め ―</p>
        </div>
    </div>
    """

    st.markdown(banner_html, unsafe_allow_html=True)
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
        if "p_submitted" not in st.session_state:
            st.session_state.p_submitted = False
        if "p_last_is_correct" not in st.session_state:
            st.session_state.p_last_is_correct = False

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
                st.session_state.p_submitted = False
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

                c_top1, c_top2 = st.columns([3, 1])
                with c_top1:
                    st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")
                with c_top2:
                    if st.button("🛠️ この問題を修正する"):
                        question_text, _ = format_question_and_answer(q)
                        st.session_state["edit_search_keyword"] = (
                            question_text
                        )
                        st.session_state["current_nav"] = "➕ データ追加・編集"
                        st.rerun()

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")

                if not st.session_state.p_submitted:
                    display_question_image(q, is_correct_view=False)

                is_sort = (
                    q.get("type") == "並び替え"
                    or "option1" in q
                    and pd.notna(q.get("option1"))
                )
                if is_sort and not st.session_state.p_submitted:
                    st.write("【選択肢】")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"1. {q.get('option1', '')}")
                        st.write(f"2. {q.get('option2', '')}")
                    with c2:
                        st.write(f"3. {q.get('option3', '')}")
                        st.write(f"4. {q.get('option4', '')}")

                correct_list = get_correct_answers_list(q, correct_ans_raw)
                num_inputs = len(correct_list)

                if not st.session_state.p_submitted:
                    with st.form(f"practice_form_{curr_idx}"):
                        user_inputs = []
                        if num_inputs > 1 and not is_sort:
                            st.caption(f"💡 解答欄が **{num_inputs}つ** あります（順不同）。")
                            for i in range(num_inputs):
                                u_in = st.text_input(
                                    f"解答 {i+1}",
                                    key=f"p_ans_{curr_idx}_{i}",
                                    placeholder=f"解答{i+1}を記入",
                                )
                                user_inputs.append(u_in)
                        else:
                            u_in = st.text_input(
                                "解答を入力",
                                placeholder="（並び替えは『2431』のように番号で入力）"
                                if is_sort
                                else "ここに解答を記入",
                            )
                            user_inputs.append(u_in)

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
                        is_correct = check_answers_multi(user_inputs, correct_list)
                        st.session_state.p_last_is_correct = is_correct
                        st.session_state.p_submitted = True
                        disp_ans = "、".join(correct_list)

                        if is_correct:
                            st.session_state.p_score += 1

                        st.session_state.p_user_answers.append(
                            {
                                "問題": question_text,
                                "あなたの解答": "、".join([u for u in user_inputs if u]),
                                "正解": disp_ans,
                                "判定": "⭕ 正解" if is_correct else "❌ 不正解",
                            }
                        )
                        st.rerun()

                    elif passed:
                        st.session_state.p_curr_idx += 1
                        st.rerun()

                else:
                    disp_ans = "、".join(correct_list)
                    if st.session_state.p_last_is_correct:
                        st.success("⭕ 正解！")
                        display_question_image(q, is_correct_view=True)
                    else:
                        st.error(f"❌ 不正解... 正解は: **{disp_ans}**")
                        display_question_image(q, is_correct_view=False)

                    exp = get_clean_str(q.get("explanation") or q.get("解説"))
                    if exp:
                        st.info(f"💡 **【解説】**: {exp}")

                    if st.button("次の問題へ ➡", use_container_width=True):
                        st.session_state.p_submitted = False
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
            elapsed_time = int(time.time() - st.session_state.exam_start_time)
            total_time_limit = 60 * 60
            remaining_time = max(0, total_time_limit - elapsed_time)
            mins, secs = divmod(remaining_time, 60)

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

            if remaining_time <= 0 or curr_idx >= total_q:
                st.balloons()
                st.markdown("## 🏁 模試終了！ 採点結果")

                score = 0
                summary_data = []
                for idx, q_item in enumerate(st.session_state.e_quiz_list):
                    q_txt, c_ans_raw = format_question_and_answer(q_item)
                    correct_list = get_correct_answers_list(q_item, c_ans_raw)
                    u_ans_list = st.session_state.e_user_answers.get(idx, [])
                    
                    is_c = check_answers_multi(u_ans_list, correct_list)
                    if is_c:
                        score += 1

                    summary_data.append(
                        {
                            "問": idx + 1,
                            "問題文": q_txt,
                            "あなたの解答": "、".join(u_ans_list),
                            "正解": "、".join(correct_list),
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

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")

                display_question_image(q, is_correct_view=False)

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

                correct_list = get_correct_answers_list(q, correct_ans_raw)
                num_inputs = len(correct_list)
                prev_vals = st.session_state.e_user_answers.get(curr_idx, [])

                with st.form(f"exam_form_{curr_idx}"):
                    curr_user_inputs = []
                    if num_inputs > 1 and not is_sort:
                        st.caption(f"💡 解答欄が **{num_inputs}つ** あります（順不同）。")
                        for i in range(num_inputs):
                            p_val = prev_vals[i] if i < len(prev_vals) else ""
                            u_in = st.text_input(
                                f"解答 {i+1}",
                                value=p_val,
                                key=f"e_ans_{curr_idx}_{i}",
                            )
                            curr_user_inputs.append(u_in)
                    else:
                        p_val = prev_vals[0] if prev_vals else ""
                        u_in = st.text_input("解答を入力してください", value=p_val)
                        curr_user_inputs.append(u_in)

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
                    st.session_state.e_user_answers[curr_idx] = curr_user_inputs
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

# --- 6. データ追加・編集モード ---
elif selected == "➕ データ追加・編集":
    st.title("➕ データ管理センター")
    st.caption("データの追加および、登録済みデータの編集・画像確認を行えます。")
    st.write("---")

    if "added_data" not in st.session_state:
        st.session_state["added_data"] = pd.DataFrame()

    # ★ 2大カテゴリに大分割（1. データの追加 / 2. データの編集・確認）
    main_tab1, main_tab2 = st.tabs(["📥 1. データの追加", "✏️ 2. データの編集・確認"])

    # ----------------------------------------------------
    # 大タブ 1: データの追加
    # ----------------------------------------------------
    with main_tab1:
        sub_tab1, sub_tab2, sub_tab3 = st.tabs(
            ["👤 キャラデータ追加", "📝 記述問題追加", "🔢 並び替え問題追加"]
        )

        with sub_tab1:
            st.subheader("👤 キャラクターマスターデータの追加")
            up_img = st.file_uploader(
                "🖼️ キャラクター画像を添付", type=["png", "jpg", "jpeg"], key="upload_char_img"
            )
            uploaded_img_name = save_uploaded_image(up_img)

            with st.form("char_form", clear_on_submit=True):
                c_name = st.text_input("名前 (name)", placeholder="例: モンキー・D・ルフィ")
                c_nickname = st.text_input("異名 (nickname)", placeholder="例: 麦わらのルフィ")
                c_fruit = st.text_input("悪魔の実 (devil_fruit)", placeholder="例: ヒトヒトの実 モデル『ニカ』")
                c_fruit_type = st.text_input("悪魔の実の種別 (fruit_type)", placeholder="例: ゾオン系 幻獣種")
                c_affil = st.text_input("所属 (affiliation)", placeholder="例: 麦わらの一味")
                c_question = st.text_input("カスタム問題文 (question)", placeholder="空欄の場合デフォルト表示")

                if st.form_submit_button("＋ キャラデータを追加"):
                    new_item = {
                        "type": "キャラデータ",
                        "name": c_name,
                        "nickname": c_nickname,
                        "devil_fruit": c_fruit,
                        "fruit_type": c_fruit_type,
                        "affiliation": c_affil,
                        "question": c_question,
                        "image": uploaded_img_name,
                    }
                    new_row = pd.DataFrame([new_item])
                    st.session_state["added_data"] = pd.concat(
                        [st.session_state["added_data"], new_row], ignore_index=True
                    )
                    st.success(
                        f"キャラデータ（画像: {uploaded_img_name or 'なし'}）を一時追加しました！"
                    )

        with sub_tab2:
            st.subheader("📝 記述式クイズの追加")
            num_answers = st.selectbox(
                "解答（正解）の項目数を選択",
                options=[1, 2, 3, 4, 5],
                index=0,
                help="複数解答がある場合は項目数を変更してください。",
            )

            col_img1, col_img2 = st.columns(2)
            with col_img1:
                q_img = st.file_uploader("🖼️ 問題用画像を添付", type=["png", "jpg", "jpeg"], key="upload_q_img")
                q_img_name = save_uploaded_image(q_img)
            with col_img2:
                c_img = st.file_uploader("🖼️ 正解表示用画像を添付 (任意)", type=["png", "jpg", "jpeg"], key="upload_c_img")
                c_img_name = save_uploaded_image(c_img)

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

                if st.form_submit_button("＋ 記述問題を追加"):
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
                            "image": q_img_name,
                            "correct_image": c_img_name,
                        }
                        for idx, a_val in enumerate(ans_inputs):
                            new_item[f"answer_{idx+1}"] = a_val

                        new_row = pd.DataFrame([new_item])
                        st.session_state["added_data"] = pd.concat(
                            [st.session_state["added_data"], new_row],
                            ignore_index=True,
                        )
                        st.success("記述問題を一時追加しました！")
                    else:
                        st.error("問題文と少なくとも1つの正解を入力してください。")

        with sub_tab3:
            st.subheader("🔢 並び替えクイズの追加")
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
                    "正解の順序（番号で指定）", placeholder="例：3214"
                )
                s_exp = st.text_area("解説", placeholder="時系列の補足などを記入")

                if st.form_submit_button("＋ 並び替え問題を追加"):
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
                        st.success("並び替え問題を一時追加しました！")
                    else:
                        st.error("必要な項目を入力してください。")

    # ----------------------------------------------------
    # 大タブ 2: データの編集・確認（画像のワンクリック確認機能付き）
    # ----------------------------------------------------
    with main_tab2:
        default_keyword = st.session_state.get("edit_search_keyword", "")

        filter_kw = st.text_input(
            "🔍 編集対象の絞り込み検索",
            value=default_keyword,
            placeholder="キャラ名や問題文、正解のキーワードを入力して絞り込み",
        )

        target_data = pd.concat(
            [df_all, st.session_state["added_data"]], ignore_index=True
        )

        if target_data.empty:
            st.info("現在表示・編集できるデータがありません。")
        else:
            if filter_kw:
                mask = (
                    target_data.astype(str)
                    .apply(
                        lambda x: x.str.contains(
                            filter_kw, case=False, na=False
                        )
                    )
                    .any(axis=1)
                )
                target_data = target_data[mask]

            st.caption(
                "💡 セルをダブルクリックすると直接書き換えられます。選択した行の画像は下部プレビューでワンクリック確認できます。"
            )

            is_char_mask = (
                target_data["type"] == "キャラデータ"
                if "type" in target_data.columns
                else pd.Series(False, index=target_data.index)
            )
            if not is_char_mask.any() and "characterid" in target_data.columns:
                is_char_mask = target_data["characterid"].notna()

            char_df = target_data[is_char_mask].copy().dropna(how="all", axis=1)
            quiz_df = target_data[~is_char_mask].copy().dropna(how="all", axis=1)

            view_tab1, view_tab2 = st.tabs(["👥 キャラクターマスター", "📝 問題集データ"])

            with view_tab1:
                st.markdown("##### 👥 キャラクターマスター 一覧")
                if char_df.empty:
                    st.caption("該当するキャラクターデータはありません。")
                else:
                    edited_char = st.data_editor(
                        char_df,
                        num_rows="dynamic",
                        use_container_width=True,
                        key="editor_char_data",
                    )
                    buffer_char = io.BytesIO()
                    with pd.ExcelWriter(buffer_char, engine="openpyxl") as writer:
                        edited_char.to_excel(writer, index=False)

                    st.download_button(
                        label="📥 キャラクターマスターをExcel出力 (`character_master.xlsx`)",
                        data=buffer_char.getvalue(),
                        file_name="character_master.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

            with view_tab2:
                st.markdown("##### 📝 記述・並び替え問題集 一覧")
                if quiz_df.empty:
                    st.caption("該当する問題集データはありません。")
                else:
                    edited_quiz = st.data_editor(
                        quiz_df,
                        num_rows="dynamic",
                        use_container_width=True,
                        key="editor_quiz_data",
                    )
                    buffer_quiz = io.BytesIO()
                    with pd.ExcelWriter(buffer_quiz, engine="openpyxl") as writer:
                        edited_quiz.to_excel(writer, index=False)

                    st.download_button(
                        label="📥 問題集データをExcel出力 (`quiz_data.xlsx`)",
                        data=buffer_quiz.getvalue(),
                        file_name="quiz_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

            st.write("---")

            # ★ 画像のワンクリック確認（プレビュー）機能
            st.markdown("### 🖼️ 画像プレビュー・確認")
            st.caption("一覧にあるデータの画像（`image` / `correct_image`）をワンクリックで選択・確認できます。")

            # 画像プレビュー候補アイテムの生成
            preview_options = {}
            for idx, row in target_data.iterrows():
                name_display = get_clean_str(row.get("name")) or get_clean_str(row.get("question"))[:20] or f"データ #{idx+1}"
                img_val = get_clean_str(row.get("image") or row.get("画像"))
                c_img_val = get_clean_str(row.get("correct_image") or row.get("正解画像"))
                
                if img_val or c_img_val:
                    label = f"[{idx+1}] {name_display} (画像: {img_val or '無'} / 正解画像: {c_img_val or '無'})"
                    preview_options[label] = row

            if preview_options:
                selected_item_label = st.selectbox(
                    "画像を確認したい対象データを選択", options=list(preview_options.keys())
                )
                if selected_item_label:
                    selected_row = preview_options[selected_item_label]
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.markdown("**【問題・キャラクター用画像】**")
                        if not display_question_image(selected_row, width=300, is_correct_view=False):
                            st.caption("⚠️ 画像ファイルが存在しないか、設定されていません。")
                    with col_p2:
                        st.markdown("**【正解表示用画像】**")
                        if not display_question_image(selected_row, width=300, is_correct_view=True):
                            st.caption("⚠️ 正解表示用画像が存在しないか、設定されていません。")
            else:
                st.info("現在表示中のデータの中に、画像ファイル名が登録されている項目はありません。")

            st.write("")
            if st.button("🔄 一時追加データ・検索フィルターをリセット"):
                st.session_state["added_data"] = pd.DataFrame()
                st.session_state["edit_search_keyword"] = ""
                st.rerun()

            st.caption(
                "※ダウンロードしたファイルをGitHubにアップロード（上書き保存）すると、本番データに反映されます。"
            )
