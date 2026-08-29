import glob
import io
import os
import random
import re
import time
import base64
import pandas as pd
import streamlit as st


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
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ["nan", "none", "<na>"]:
        return ""
    return s


# 画像表示ヘルパー関数
def display_question_image(q_data, width=300, caption=None, show_caption=False):
    img_val = get_clean_str(q_data.get("image") or q_data.get("画像"))
    if not img_val:
        st.caption("📷 画像データなし")
        return False

    cap = (caption or f"ファイル: {img_val}") if show_caption else None

    if img_val.startswith("http://") or img_val.startswith("https://"):
        st.image(img_val, width=width, caption=cap)
        return True

    imgPath = (
        img_val
        if os.path.exists(img_val)
        else os.path.join("images", img_val)
    )
    if os.path.exists(imgPath):
        st.image(imgPath, width=width, caption=cap)
        return True

    st.caption("⚠️ 画像ファイルが見つかりません")
    return False


# 正解リスト抽出ヘルパー
def get_correct_answers_list(q, correct_ans_str):
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


# 正解判定共通ロジック
def check_answers_multi(user_inputs, correct_answers):
    user_clean = [str(u).strip() for u in user_inputs if str(u).strip()]
    correct_clean = [str(c).strip() for c in correct_answers if str(c).strip()]

    if len(user_clean) != len(correct_clean):
        return False

    return set(user_clean) == set(correct_clean)


# キャラマスターデータから問題文と正解を確定させるロジック
def format_question_and_answer(q):
    raw_question = get_clean_str(
        q.get("question") or q.get("問題") or q.get("Question") or q.get("question_text")
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

    return "このキャラクターの名前は？", name


# --- ページ基本設定 ---
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策",
    page_icon="🏴‍☠️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "current_nav" not in st.session_state:
    st.session_state["current_nav"] = "ホーム"

df_all = load_all_data()

# --- 1. ホーム画面 ---
if st.session_state["current_nav"] == "ホーム":
    all_imgs = (
        glob.glob("images/*.png")
        + glob.glob("images/*.jpg")
        + glob.glob("images/*.jpeg")
        + glob.glob("*.png")
        + glob.glob("*.jpg")
    )

    grid_imgs_html = ""
    if all_imgs:
        sample_imgs = [random.choice(all_imgs) for _ in range(120)]
        for img_path in sample_imgs:
            try:
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    ext = img_path.split(".")[-1].lower()
                    mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                    grid_imgs_html += f'<img src="data:{mime};base64,{b64}" class="bg-tile" />'
            except Exception:
                continue

    # メインカード内に全要素（バナー＋モザイク＋ボタン群）を包含するスタイル
    home_style_html = f"""
    <style>
    .main-card-container {{
        position: relative;
        width: 100%;
        max-width: 900px;
        margin: 0 auto 25px auto;
        border-radius: 20px;
        overflow: hidden;
        border: 2px solid #333;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        background-color: #0d0d0d;
        padding: 30px 20px;
    }}
    
    .mosaic-bg-full {{
        position: absolute;
        top: -10%;
        left: 0;
        width: 100%;
        height: 130%;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
        grid-auto-rows: 80px;
        gap: 2px;
        opacity: 0.7;
        z-index: 1;
    }}
    
    .bg-tile {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}

    .card-content {{
        position: relative;
        z-index: 2;
        display: flex;
        flex-direction: column;
        gap: 20px;
    }}

    .banner-card {{
        width: 100%;
        background: rgba(0, 0, 0, 0.65);
        backdrop-filter: blur(4px);
        padding: 25px 20px;
        border-radius: 14px;
        border: 3px solid #ffcc00;
        text-align: center;
        box-shadow: 0 0 20px rgba(255, 204, 0, 0.3);
    }}
    
    .banner-card h1 {{
        margin: 0 0 6px 0;
        font-size: 2.2rem;
        color: #ffffff;
        font-weight: 900;
        text-shadow: 2px 2px 5px #000;
    }}
    
    .banner-card p {{
        margin: 0;
        color: #ffcc00;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 2px;
    }}

    /* Streamlitのボタンを黒枠カード内に馴染ませるCSS */
    div[data-testid="stColumn"] > div > div > button {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        color: #111111 !important;
        border: 1px solid #cccccc !important;
        border-radius: 10px !important;
        padding: 14px 20px !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        text-align: center !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }}

    div[data-testid="stColumn"] > div > div > button:hover {{
        background-color: #ffcc00 !important;
        color: #000000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(255, 204, 0, 0.5) !important;
    }}
    </style>

    <div class="main-card-container">
        <div class="mosaic-bg-full">
            {grid_imgs_html if grid_imgs_html else '<div style="grid-column: 1/-1; text-align:center; color:#888; padding-top:100px;">（画像をimagesフォルダに入れると背景に表示されます）</div>'}
        </div>
        <div class="card-content">
            <div class="banner-card">
                <h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1>
                <p>― 最強のデータベースを脳に刻め ―</p>
            </div>
    """

    st.markdown(home_style_html, unsafe_allow_html=True)

    # 黒枠カードの中でボタンを縦一列に配置
    menu_items = [
        ("🏆 本番模試（50問/60分）", "🏆 本番模試（50問/60分）"),
        ("💻 練習モード", "📖 練習モード"),
        ("🔥 苦手克服", "🔥 苦手克服"),
        ("🔍 AI検索モード", "🔍 AI検索モード"),
        ("➕ データ追加・編集", "➕ データ追加・編集"),
    ]

    for label, target_nav in menu_items:
        col = st.columns(1)[0]
        with col:
            if st.button(label, key=f"home_nav_{target_nav}", use_container_width=True):
                st.session_state["current_nav"] = target_nav
                st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

    if not df_all.empty:
        st.info(f"📊 現在の登録データ総数: **{len(df_all)}** 件")
    else:
        st.warning("現在、読み込めるExcelデータ（.xlsx）がありません。")

# --- ホーム戻る用共通ヘッダー ---
else:
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("🏠 ホームへ戻る", use_container_width=True):
            st.session_state["current_nav"] = "ホーム"
            st.rerun()

# --- 2. 練習モード ---
if st.session_state["current_nav"] == "📖 練習モード":
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
            st.success(f"全 {len(df_all)} 問の中から自由に出題条件を設定できます。")

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
                elif q_type_filter == "並び替え問題" and "type" in target_df.columns:
                    target_df = target_df[target_df["type"] == "並び替え"]
                elif q_type_filter == "キャラマスター" and "type" in target_df.columns:
                    target_df = target_df[target_df["type"] == "キャラデータ"]

                if target_df.empty:
                    target_df = df_all.copy()

                shuffled = target_df.sample(n=min(num_q, len(target_df))).reset_index(
                    drop=True
                )
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

                c_top1, c_top2 = st.columns([3, 1])
                with c_top1:
                    st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")
                with c_top2:
                    if st.button("🛠️ この問題を修正する"):
                        img_name = get_clean_str(q.get("image") or q.get("画像"))
                        char_name = get_clean_str(q.get("name") or q.get("名前"))

                        target_kw = img_name or char_name
                        if not target_kw:
                            target_kw, _ = format_question_and_answer(q)

                        st.session_state["edit_search_keyword"] = target_kw
                        st.session_state["edit_active_tab"] = 1
                        st.session_state["selected_char_index"] = 0
                        st.session_state["selected_quiz_index"] = 0
                        st.session_state["current_nav"] = "➕ データ追加・編集"
                        st.rerun()

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")

                is_char_q = "このキャラクターの名前は？" in question_text or bool(
                    q.get("image") or q.get("画像")
                )
                if is_char_q:
                    display_question_image(q, show_caption=False)

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
                    disp_ans = "、".join(correct_list)

                    if is_correct:
                        st.success("⭕ 正解！")
                        st.session_state.p_score += 1
                    else:
                        st.error(f"❌ 不正解... 正解は: **{disp_ans}**")

                    exp = get_clean_str(q.get("explanation") or q.get("解説"))
                    if exp:
                        st.caption(f"💡 【解説】: {exp}")

                    st.session_state.p_user_answers.append(
                        {
                            "問題": question_text,
                            "あなたの解答": "、".join([u for u in user_inputs if u]),
                            "正解": disp_ans,
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

# --- 3. 本番模試 ---
elif st.session_state["current_nav"] == "🏆 本番模試（50問/60分）":
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

                is_char_q = "このキャラクターの名前は？" in question_text or bool(
                    q.get("image") or q.get("画像")
                )
                if is_char_q:
                    display_question_image(q, show_caption=False)

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
elif st.session_state["current_nav"] == "🔥 苦手克服":
    st.subheader("🔥 苦手克服モード")
    st.info("間違えた問題やチェックした問題を重点的に復習できます。")

# --- 5. AI検索モード ---
elif st.session_state["current_nav"] == "🔍 AI検索モード":
    st.title("🔍 AI検索モード")
    st.caption("〜 データベース爆速逆引き図鑑 〜")
    st.write("---")

    if df_all.empty:
        st.error("データが見つかりません。Excelファイルを配置してください。")
    else:
        search_query = st.text_input(
            "🔍 検索キーワード（名前・悪魔の実・異名・問題文・正解など）",
            "",
            placeholder="例: レイジュ、バギー、悪魔の実、シャンクス",
            key="ai_search_query_input",
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
            filtered_df = df_all[mask].reset_index(drop=True)
        else:
            filtered_df = df_all.reset_index(drop=True)

        if filtered_df.empty:
            st.warning("該当するデータが見つかりませんでした。")
        else:
            is_char_mask = (
                filtered_df["type"] == "キャラデータ"
                if "type" in filtered_df.columns
                else pd.Series(False, index=filtered_df.index)
            )
            if not is_char_mask.any() and "characterid" in filtered_df.columns:
                is_char_mask = filtered_df["characterid"].notna()

            char_search_df = (
                filtered_df[is_char_mask]
                .copy()
                .dropna(how="all", axis=1)
                .reset_index(drop=True)
            )
            quiz_search_df = (
                filtered_df[~is_char_mask]
                .copy()
                .dropna(how="all", axis=1)
                .reset_index(drop=True)
            )

            tab_search1, tab_search2 = st.tabs(
                ["👥 キャラクターマスター", "📝 問題集データ"]
            )

            with tab_search1:
                if char_search_df.empty:
                    st.caption("該当するキャラクターデータはありません。")
                else:
                    if "ai_selected_char_index" not in st.session_state:
                        st.session_state["ai_selected_char_index"] = 0

                    btn_cols = st.columns(min(len(char_search_df), 6))
                    for i, row in char_search_df.head(6).iterrows():
                        c_name = (
                            get_clean_str(row.get("name") or row.get("名前"))
                            or f"キャラ{i+1}"
                        )
                        with btn_cols[i % 6]:
                            if st.button(
                                f"👤 {c_name}",
                                key=f"ai_btn_char_{i}",
                                use_container_width=True,
                            ):
                                st.session_state["ai_selected_char_index"] = i
                                st.rerun()

                    curr_c_idx = min(
                        st.session_state["ai_selected_char_index"],
                        len(char_search_df) - 1,
                    )
                    sel_row = char_search_df.iloc[curr_c_idx]
                    char_label = get_clean_str(
                        sel_row.get("name") or sel_row.get("名前")
                    )
                    char_id = get_clean_str(sel_row.get("characterid"))

                    st.info(
                        f"📌 選択中のキャラクター: **{char_label}** {f'(ID: {char_id})' if char_id else ''}"
                    )

                    card_col1, card_col2 = st.columns([1, 2])
                    with card_col1:
                        display_question_image(
                            sel_row, width=280, show_caption=True
                        )
                    with card_col2:
                        st.write(
                            f"**異名/通り名:** {get_clean_str(sel_row.get('nickname') or sel_row.get('異名')) or 'なし'}"
                        )
                        st.write(
                            f"**悪魔の実:** {get_clean_str(sel_row.get('devil_fruit') or sel_row.get('悪魔の実')) or 'なし'}"
                        )
                        st.write(
                            f"**系統/種類:** {get_clean_str(sel_row.get('fruit_type')) or 'なし'}"
                        )
                        st.write(
                            f"**所属/組織:** {get_clean_str(sel_row.get('affiliation') or sel_row.get('所属')) or 'なし'}"
                        )
                        st.write(
                            f"**画像ファイル名/URL:** `{get_clean_str(sel_row.get('image') or sel_row.get('画像'))}`"
                        )

                    st.dataframe(
                        char_search_df,
                        on_select="rerun",
                        selection_mode="single-row",
                        use_container_width=True,
                        key="df_ai_char_select",
                    )

            with tab_search2:
                if quiz_search_df.empty:
                    st.caption("該当する問題集データはありません。")
                else:
                    if "ai_selected_quiz_index" not in st.session_state:
                        st.session_state["ai_selected_quiz_index"] = 0

                    curr_q_idx = min(
                        st.session_state["ai_selected_quiz_index"],
                        len(quiz_search_df) - 1,
                    )
                    sel_q_row = quiz_search_df.iloc[curr_q_idx]
                    q_t, c_a = format_question_and_answer(sel_q_row)

                    st.info(f"📌 選択中の問題: **第 {curr_q_idx + 1} 問**")
                    q_col1, q_col2 = st.columns([1, 2])
                    with q_col1:
                        display_question_image(
                            sel_q_row, width=280, show_caption=True
                        )
                    with q_col2:
                        st.write(f"**問題文:** {q_t}")
                        st.write(f"**正解:** {c_a}")
                        st.write(
                            f"**解説:** {get_clean_str(sel_q_row.get('explanation') or sel_q_row.get('解説')) or 'なし'}"
                        )
                        st.write(
                            f"**画像ファイル名/URL:** `{get_clean_str(sel_q_row.get('image') or sel_q_row.get('画像'))}`"
                        )

                    st.dataframe(
                        quiz_search_df,
                        on_select="rerun",
                        selection_mode="single-row",
                        use_container_width=True,
                        key="df_ai_quiz_select",
                    )

# --- 6. データ追加・編集モード ---
elif st.session_state["current_nav"] == "➕ データ追加・編集":
    st.title("➕ データ追加・編集センター")
    st.caption("新規データの登録や、データの確認・リアルタイム編集が行えます。")
    st.write("---")

    if "added_data" not in st.session_state:
        st.session_state["added_data"] = pd.DataFrame()

    default_tab_idx = st.session_state.pop("edit_active_tab", 0)

    tab_selection = st.radio(
        "機能切替",
        ["➕ 1. データの追加", "✏️ 2. データの編集"],
        index=default_tab_idx,
        horizontal=True,
        label_visibility="collapsed",
    )

    if tab_selection == "➕ 1. データの追加":
        st.subheader("📝 新しいデータの追加")
        sub_add_tab1, sub_add_tab2, sub_add_tab3 = st.tabs(
            ["👤 キャラデータ", "📝 記述問題", "🔢 並び替え問題"]
        )

        with sub_add_tab1:
            st.markdown("##### キャラクターマスターの追加")
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
                        [st.session_state["added_data"], new_row],
                        ignore_index=True,
                    )
                    st.success(
                        "キャラデータを一時追加しました！「2. データの編集」タブで確認・編集できます。"
                    )

        with sub_add_tab2:
            st.markdown("##### 記述式クイズの追加")
            num_answers = st.selectbox(
                "解答（正解）の項目数を選択",
                options=[1, 2, 3, 4, 5],
                index=0,
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
                            placeholder="例：正解",
                            key=f"ans_input_{i}",
                        )
                        ans_inputs.append(ans_val)

                exp_text = st.text_area("解説・関連情報")
                genre = st.text_input("ジャンル/関連エピソード")

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
                        st.success("記述問題を一時追加しました！")

        with sub_add_tab3:
            st.markdown("##### 並び替えクイズの追加")
            with st.form("sort_form", clear_on_submit=True):
                sq_text = st.text_area("問題文")
                col1, col2 = st.columns(2)
                with col1:
                    opt1 = st.text_input("選択肢 1 (●)")
                    opt2 = st.text_input("選択肢 2 (△)")
                with col2:
                    opt3 = st.text_input("選択肢 3 (□)")
                    opt4 = st.text_input("選択肢 4 (×)")

                s_answer = st.text_input("正解の順序（番号で指定）")
                s_exp = st.text_area("解説")

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
                        st.success("並び替え問題を一時追加しました！")

    elif tab_selection == "✏️ 2. データの編集":
        st.subheader("✏️ データの確認・画像チェック・リアルタイム編集")

        default_keyword = st.session_state.get("edit_search_keyword", "")
        filter_kw = st.text_input(
            "🔍 編集対象問題の絞り込み検索",
            value=default_keyword,
            placeholder="キーワード（名前・問題文・正解など）で検索",
            key="edit_search_keyword_input",
        )
        st.session_state["edit_search_keyword"] = filter_kw

        target_data = pd.concat(
            [df_all, st.session_state["added_data"]], ignore_index=True
        )

        if not target_data.empty:
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

            is_char_mask = (
                target_data["type"] == "キャラデータ"
                if "type" in target_data.columns
                else pd.Series(False, index=target_data.index)
            )
            if not is_char_mask.any() and "characterid" in target_data.columns:
                is_char_mask = target_data["characterid"].notna()

            char_df = (
                target_data[is_char_mask]
                .copy()
                .dropna(how="all", axis=1)
                .reset_index(drop=True)
            )
            quiz_df = (
                target_data[~is_char_mask]
                .copy()
                .dropna(how="all", axis=1)
                .reset_index(drop=True)
            )

            sub_edit_tab1, sub_edit_tab2 = st.tabs(
                ["👥 キャラクターマスター", "📝 問題集データ"]
            )

            with sub_edit_tab1:
                st.markdown("##### 👥 キャラクターマスター 一覧・編集")
                if not char_df.empty:
                    st.dataframe(
                        char_df,
                        use_container_width=True,
                        key="df_char_edit",
                    )

            with sub_edit_tab2:
                st.markdown("##### 📝 記述・並び替え問題集 一覧・編集")
                if not quiz_df.empty:
                    st.dataframe(
                        quiz_df,
                        use_container_width=True,
                        key="df_quiz_edit",
                    )
