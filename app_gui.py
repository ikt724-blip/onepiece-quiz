import base64
import glob
import io
import math
import os
import random
import re
import time
import pandas as pd
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


# --- 🖼️ 画像表示・フォルダ自動探索関数（日本語ファイル名完全対応版） ---
def display_question_image(row, width=200, show_caption=True):
    """
    指定された行データから画像パスを抽出し、
    日本語ファイル名でもエラーが出ないよう安全に画像を表示する関数
    """
    img_sources = []
    IMAGE_DIRS = ["images", "img", "static/images", "assets", "data/images", "."]

    for col in ["question_image", "image", "answer_image", "画像"]:
        if col in row and pd.notna(row[col]):
            val = str(row[col]).strip()
            if val and val.lower() != "nan":
                for img_item in val.replace("\n", ",").split(","):
                    cleaned_path = img_item.strip()
                    if cleaned_path and cleaned_path not in img_sources:
                        img_sources.append(cleaned_path)

    if not img_sources:
        st.info("📷 画像データなし")
        return

    for idx, raw_path in enumerate(img_sources):
        resolved_path = None

        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            resolved_path = raw_path
        else:
            if os.path.exists(raw_path):
                resolved_path = raw_path
            else:
                filename = os.path.basename(raw_path)
                for d in IMAGE_DIRS:
                    test_path = os.path.join(d, filename)
                    if os.path.exists(test_path):
                        resolved_path = test_path
                        break

        cap = None
        if show_caption:
            q_text = str(
                row.get("question") or row.get("name") or ""
            ).strip()
            cap = (
                f"画像 {idx + 1}"
                if not q_text
                else f"【画像 {idx + 1}】 {q_text[:20]}"
            )

        if resolved_path:
            try:
                if resolved_path.startswith("http"):
                    st.image(resolved_path, caption=cap, width=width)
                else:
                    with Image.open(resolved_path) as img:
                        img_bytes = img.copy()
                        if width:
                            st.image(
                                img_bytes,
                                caption=cap,
                                width=width,
                            )
                        else:
                            st.image(
                                img_bytes,
                                caption=cap,
                                use_container_width=True,
                            )
            except Exception as e:
                st.warning(f"⚠️ 画像の表示エラー: {raw_path} ({e})")
        else:
            st.info(f"📷 画像ファイルが見つかりません: `{raw_path}`")


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
                t.strip()
                for t in re.split(r"[、,]", correct_ans_str)
                if t.strip()
            ]
        else:
            answers = [correct_ans_str.strip()]

    return answers


# 正解判定共通ロジック
def check_answers_multi(user_inputs, correct_answers):
    user_clean = [str(u).strip() for u in user_inputs if str(u).strip()]
    correct_clean = [
        str(c).strip() for c in correct_answers if str(c).strip()
    ]

    if len(user_clean) != len(correct_clean):
        return False

    return set(user_clean) == set(correct_clean)


# キャラマスターデータから問題文と正解を確定させるロジック
def format_question_and_answer(q):
    raw_question = get_clean_str(
        q.get("question")
        or q.get("問題")
        or q.get("Question")
        or q.get("question_text")
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
        return (
            f"「{name}」の主な所属（組織・海賊団など）は？",
            affiliation,
        )

    if nickname and name:
        return f"「{name}」の異名（通り名）は？", nickname

    if name:
        return "このキャラクターの名前は？", name

    return "このキャラクターの名前は？", name


# --- ページ基本設定 ---
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策",
    page_icon="🏴‍☠️",
    layout="wide",
)

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
        key="nav_menu_main",
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

    # アプリ起動・更新ごとに全キャラクターの画像順をランダム化してセッションに保持
    if "shuffled_bg_images" not in st.session_state:
        shuffled = all_imgs.copy()
        random.shuffle(shuffled)
        st.session_state["shuffled_bg_images"] = shuffled

    current_bg_imgs = st.session_state["shuffled_bg_images"]

    grid_imgs_html = ""
    if current_bg_imgs:
        # 画面更新時のランダム順を元に、途切れなく上から下へ流すため2周分配置
        full_loop_imgs = current_bg_imgs + current_bg_imgs
        for img_path in full_loop_imgs:
            try:
                with Image.open(img_path) as img:
                    buffered = io.BytesIO()
                    ext = img_path.split(".")[-1].lower()
                    fmt = "JPEG" if ext in ["jpg", "jpeg"] else "PNG"
                    mime = (
                        "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                    )
                    img.save(buffered, format=fmt)
                    b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
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
        top: 0;
        left: 0;
        width: 100%;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
        grid-auto-rows: 80px;
        gap: 6px;
        padding: 6px;
        opacity: 0.85;
        /* 全キャラが上から下へ流れるアニメーション */
        animation: stream-down 25s linear infinite;
    }}

    @keyframes stream-down {{
        0% {{
            transform: translateY(-50%);
        }}
        100% {{
            transform: translateY(0%);
        }}
    }}
    
    .bg-tile {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 6px;
    }}

    .center-overlay {{
        position: relative;
        z-index: 2;
        background: rgba(0, 0, 0, 0.70);
        backdrop-filter: blur(4px);
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
            {grid_imgs_html if grid_imgs_html else '<div style="grid-column: 1/-1; text-align:center; color:#888; padding-top:180px;">（画像を追加すると背景に全キャラが流れます）</div>'}
        </div>
        <div class="center-overlay">
            <h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1>
            <p>― 最強のデータベースを脳に刻め ―</p>
        </div>
    </div>
    """

    st.markdown(banner_html, unsafe_allow_html=True)
    st.write("")

    if st.button("🔀 背景画像のランダム並び順をシャッフル"):
        shuffled = all_imgs.copy()
        random.shuffle(shuffled)
        st.session_state["shuffled_bg_images"] = shuffled
        st.rerun()

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
                    "問題タイプ",
                    ["すべて", "記述問題", "並び替え問題", "キャラマスター"],
                )

            if st.button("🚀 練習を開始する", use_container_width=True):
                target_df = df_all.copy()
                if (
                    q_type_filter == "記述問題"
                    and "type" in target_df.columns
                ):
                    target_df = target_df[target_df["type"] == "記述"]
                elif (
                    q_type_filter == "並び替え問題"
                    and "type" in target_df.columns
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

                c_top1, c_top2 = st.columns([3, 1])
                with c_top1:
                    st.markdown(
                        f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問"
                    )
                with c_top2:
                    if st.button("🛠️ この問題を修正する"):
                        img_name = get_clean_str(
                            q.get("image") or q.get("画像")
                        )
                        char_name = get_clean_str(
                            q.get("name") or q.get("名前")
                        )

                        target_kw = img_name or char_name
                        if not target_kw:
                            target_kw, _ = format_question_and_answer(q)

                        st.session_state["edit_search_keyword"] = target_kw
                        st.session_state["edit_active_tab"] = 1
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
                        st.caption(
                            f"💡 解答欄が **{num_inputs}つ** あります（順不同）。"
                        )
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
                            "あなたの解答": "、".join(
                                [u for u in user_inputs if u]
                            ),
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

            if st.button(
                "🔥 模試を開始する（タイマースタート）",
                use_container_width=True,
            ):
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
                st.dataframe(
                    pd.DataFrame(summary_data), use_container_width=True
                )

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
                        st.caption(
                            f"💡 解答欄が **{num_inputs}つ** あります（順不同）。"
                        )
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
                    st.session_state.e_user_answers[
                        curr_idx
                    ] = curr_user_inputs
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
    st.caption(
        "〜 キャラクターマスタ＆問題データベース 爆速逆引き図鑑 〜"
    )
    st.write("---")

    if df_all.empty:
        st.error("データが見つかりません。Excelファイルを配置してください。")
    else:
        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
        with col_s1:
            search_query = st.text_input(
                "キーワード検索",
                "",
                placeholder="名前・悪魔の実・技・所属・問題文・解説など",
            )
        with col_s2:
            type_options = (
                ["すべて"] + list(df_all["type"].dropna().unique())
                if "type" in df_all.columns
                else ["すべて"]
            )
            filter_type = st.selectbox("データ種別", type_options)
        with col_s3:
            filter_fruit = st.selectbox(
                "悪魔の実", ["すべて", "能力者のみ", "非能力者"]
            )

        filtered_df = df_all.copy()

        if search_query:
            mask = (
                filtered_df.astype(str)
                .apply(
                    lambda x: x.str.contains(
                        search_query, case=False, na=False
                    )
                )
                .any(axis=1)
            )
            filtered_df = filtered_df[mask]

        if filter_type != "すべて" and "type" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["type"] == filter_type]

        if filter_fruit != "すべて" and "devil_fruit" in filtered_df.columns:
            if filter_fruit == "能力者のみ":
                filtered_df = filtered_df[
                    filtered_df["devil_fruit"].notna()
                    & (filtered_df["devil_fruit"] != "")
                ]
            elif filter_fruit == "非能力者":
                filtered_df = filtered_df[
                    filtered_df["devil_fruit"].isna()
                    | (filtered_df["devil_fruit"] == "")
                ]

        filtered_df = filtered_df.reset_index(drop=True)

        if filtered_df.empty:
            st.warning("該当するデータが見つかりませんでした。")
        else:
            if "search_selected_index" not in st.session_state:
                st.session_state["search_selected_index"] = 0

            sel_idx = min(
                st.session_state["search_selected_index"],
                len(filtered_df) - 1,
            )
            selected_item = filtered_df.iloc[sel_idx]

            c_name = (
                get_clean_str(
                    selected_item.get("name") or selected_item.get("名前")
                )
                or "詳細情報"
            )
            c_id = get_clean_str(selected_item.get("characterid"))

            st.info(
                f"📌 **【選択中】: {c_name}** {f'(ID: {c_id})' if c_id else ''}"
            )

            card_col1, card_col2 = st.columns([1, 2])
            with card_col1:
                display_question_image(
                    selected_item, width=280, show_caption=True
                )
            with card_col2:
                name_val = get_clean_str(
                    selected_item.get("name") or selected_item.get("名前")
                )
                if name_val:
                    st.markdown(f"### {name_val}")

                nick = get_clean_str(
                    selected_item.get("nickname") or selected_item.get("異名")
                )
                if nick:
                    st.write(f"**異名/通り名:** {nick}")

                fruit = get_clean_str(
                    selected_item.get("devil_fruit")
                    or selected_item.get("悪魔の実")
                )
                if fruit:
                    st.write(f"**悪魔の実:** {fruit}")

                ftype = get_clean_str(selected_item.get("fruit_type"))
                if ftype:
                    st.write(f"**系統:** {ftype}")

                aff = get_clean_str(
                    selected_item.get("affiliation")
                    or selected_item.get("所属")
                )
                if aff:
                    st.write(f"**所属:** {aff}")

                q_text, a_text = format_question_and_answer(selected_item)
                if q_text and not name_val:
                    st.write(f"**問題:** {q_text}")
                    st.write(f"**正解:** {a_text}")

                exp = get_clean_str(
                    selected_item.get("explanation")
                    or selected_item.get("解説")
                )
                if exp:
                    st.write(f"**解説:** {exp}")

                if st.button(
                    "🛠️ このデータを編集・修正する", use_container_width=True
                ):
                    target_kw = (
                        name_val
                        or get_clean_str(
                            selected_item.get("image")
                            or selected_item.get("画像")
                        )
                        or q_text
                    )
                    st.session_state["edit_search_keyword"] = target_kw
                    st.session_state["edit_active_tab"] = 1
                    st.session_state["current_nav"] = "➕ データ追加・編集"
                    st.rerun()

            st.write("")
            st.caption(
                f"💡 表の行を選択すると、詳細プレビューが更新されます。（該当件数: {len(filtered_df)} 件）"
            )

            search_event = st.dataframe(
                filtered_df,
                on_select="rerun",
                selection_mode="single-row",
                use_container_width=True,
                key="df_search_select",
            )

            if (
                search_event
                and hasattr(search_event, "selection")
                and search_event.selection.get("rows")
            ):
                picked_row = search_event.selection["rows"][0]
                if picked_row != st.session_state["search_selected_index"]:
                    st.session_state["search_selected_index"] = picked_row
                    st.rerun()


# --- 6. データ追加・編集モード ---
elif selected == "➕ データ追加・編集":
    st.title("➕ データ追加・編集センター")
    st.caption(
        "新しいクイズデータの作成や、既存データのリアルタイム確認・簡単編集が行えます。"
    )
    st.write("---")

    if "added_data" not in st.session_state:
        st.session_state["added_data"] = pd.DataFrame()

    default_tab_idx = st.session_state.pop("edit_active_tab", 0)

    tab_selection = st.radio(
        "機能切替",
        ["➕ 1. データの追加", "✏️ 2. データの編集・修正"],
        index=default_tab_idx,
        horizontal=True,
        label_visibility="collapsed",
    )

    if tab_selection == "➕ 1. データの追加":
        st.subheader("📝 新しいデータの追加")

        (
            add_tab_char,
            add_tab_1to1,
            add_tab_multi,
            add_tab_order,
            add_tab_6char,
            add_tab_pair,
            add_tab_free,
        ) = st.tabs(
            [
                "👤 キャラデータ",
                "🎯 一問一答",
                "☑️ 一問多答",
                "🔢 順序選択",
                "🔤 6文字並べ替え",
                "🔗 組み合わせ",
                "✏️ 自由記述",
            ]
        )

        with add_tab_char:
            st.markdown("##### キャラクターマスターの追加")
            with st.form("char_form", clear_on_submit=True):
                c_id = st.text_input("キャラクターID", placeholder="例: 001")
                c_name = st.text_input(
                    "名前（必須）", placeholder="例: モンキー・D・ルフィ"
                )
                c_img = st.text_input(
                    "キャラクター画像（ファイル名 / URL）",
                    placeholder="例: luffy.png",
                )
                c_nick = st.text_input(
                    "異名・通り名", placeholder="例: 麦わらのルフィ"
                )
                c_fruit = st.text_input(
                    "悪魔の実",
                    placeholder="例: ヒトヒトの実 モデル『ニカ』",
                )
                c_ftype = st.selectbox(
                    "悪魔の実の系統",
                    [
                        "",
                        "ゾオン系",
                        "パラミシア系",
                        "ロギア系",
                        "身体特徴・その他",
                    ],
                )
                c_aff = st.text_input(
                    "所属・組織", placeholder="例: 麦わらの一味"
                )

                if st.form_submit_button("👤 キャラデータを追加"):
                    if c_name:
                        new_item = {
                            "type": "キャラデータ",
                            "characterid": c_id,
                            "name": c_name,
                            "image": c_img,
                            "nickname": c_nick,
                            "devil_fruit": c_fruit,
                            "fruit_type": c_ftype,
                            "affiliation": c_aff,
                        }
                        st.session_state["added_data"] = pd.concat(
                            [
                                st.session_state["added_data"],
                                pd.DataFrame([new_item]),
                            ],
                            ignore_index=True,
                        )
                        st.success(f"「{c_name}」を追加しました！")
                    else:
                        st.error("キャラクター名は必須項目です。")

        with add_tab_1to1:
            st.markdown("##### 一問一答クイズの追加")
            with st.form("form_1to1", clear_on_submit=True):
                q_text = st.text_area("問題文（必須）")
                col_img1, col_img2 = st.columns(2)
                q_img = col_img1.text_input("問題画像（ファイル名 / URL）")
                a_img = col_img2.text_input(
                    "正答・解説画像（ファイル名 / URL）"
                )

                c1, c2 = st.columns(2)
                opt1 = c1.text_input("選択肢 1")
                opt2 = c1.text_input("選択肢 2")
                opt3 = c2.text_input("選択肢 3")
                opt4 = c2.text_input("選択肢 4")

                correct_opt = st.selectbox(
                    "正解の選択肢",
                    ["選択肢 1", "選択肢 2", "選択肢 3", "選択肢 4"],
                )
                exp_text = st.text_area("解説")

                if st.form_submit_button("🎯 一問一答を追加"):
                    opts = [opt1, opt2, opt3, opt4]
                    ans_map = {
                        "選択肢 1": opt1,
                        "選択肢 2": opt2,
                        "選択肢 3": opt3,
                        "選択肢 4": opt4,
                    }
                    if q_text and all(opts):
                        new_item = {
                            "type": "一問一答",
                            "question": q_text,
                            "question_image": q_img,
                            "answer_image": a_img,
                            "image": q_img or a_img,
                            "option1": opt1,
                            "option2": opt2,
                            "option3": opt3,
                            "option4": opt4,
                            "answer": ans_map[correct_opt],
                            "explanation": exp_text,
                        }
                        st.session_state["added_data"] = pd.concat(
                            [
                                st.session_state["added_data"],
                                pd.DataFrame([new_item]),
                            ],
                            ignore_index=True,
                        )
                        st.success("一問一答問題を追加しました！")
                    else:
                        st.error("入力漏れがあります。")

        with add_tab_multi:
            st.markdown("##### 一問多答クイズの追加")
            with st.form("form_multi", clear_on_submit=True):
                q_text = st.text_area("問題文（必須）")
                col_img1, col_img2 = st.columns(2)
                q_img = col_img1.text_input("問題画像")
                a_img = col_img2.text_input("正答・解説画像")

                c1, c2 = st.columns(2)
                opt1 = c1.text_input("選択肢 1")
                opt2 = c1.text_input("選択肢 2")
                opt3 = c2.text_input("選択肢 3")
                opt4 = c2.text_input("選択肢 4")

                st.write("**正解チェック**")
                chk1 = st.checkbox("選択肢 1")
                chk2 = st.checkbox("選択肢 2")
                chk3 = st.checkbox("選択肢 3")
                chk4 = st.checkbox("選択肢 4")
                exp_text = st.text_area("解説")

                if st.form_submit_button("☑️ 一問多答を追加"):
                    answers = []
                    if chk1 and opt1:
                        answers.append(opt1)
                    if chk2 and opt2:
                        answers.append(opt2)
                    if chk3 and opt3:
                        answers.append(opt3)
                    if chk4 and opt4:
                        answers.append(opt4)

                    if q_text and all([opt1, opt2, opt3, opt4]) and answers:
                        new_item = {
                            "type": "一問多答",
                            "question": q_text,
                            "question_image": q_img,
                            "answer_image": a_img,
                            "image": q_img or a_img,
                            "option1": opt1,
                            "option2": opt2,
                            "option3": opt3,
                            "option4": opt4,
                            "answer": "、".join(answers),
                            "explanation": exp_text,
                        }
                        st.session_state["added_data"] = pd.concat(
                            [
                                st.session_state["added_data"],
                                pd.DataFrame([new_item]),
                            ],
                            ignore_index=True,
                        )
                        st.success("一問多答問題を追加しました！")

        with add_tab_order:
            st.markdown("##### 順序選択クイズの追加")
            with st.form("form_order", clear_on_submit=True):
                q_text = st.text_area("問題文（必須）")
                col_img1, col_img2 = st.columns(2)
                q_img = col_img1.text_input("問題画像")
                a_img = col_img2.text_input("正答・解説画像")

                c1, c2 = st.columns(2)
                opt1 = c1.text_input("選択肢 1")
                opt2 = c1.text_input("選択肢 2")
                opt3 = c2.text_input("選択肢 3")
                opt4 = c2.text_input("選択肢 4")

                order_ans = st.text_input("正解の順序（例: 2143）")
                exp_text = st.text_area("解説")

                if st.form_submit_button("🔢 順序選択を追加"):
                    if (
                        q_text
                        and all([opt1, opt2, opt3, opt4])
                        and order_ans
                    ):
                        new_item = {
                            "type": "順序選択",
                            "question": q_text,
                            "question_image": q_img,
                            "answer_image": a_img,
                            "image": q_img or a_img,
                            "option1": opt1,
                            "option2": opt2,
                            "option3": opt3,
                            "option4": opt4,
                            "answer": order_ans,
                            "explanation": exp_text,
                        }
                        st.session_state["added_data"] = pd.concat(
                            [
                                st.session_state["added_data"],
                                pd.DataFrame([new_item]),
                            ],
                            ignore_index=True,
                        )
                        st.success("順序選択問題を追加しました！")

        with add_tab_6char:
            st.markdown("##### 6文字並べ替えクイズの追加")
            with st.form("form_6char", clear_on_submit=True):
                q_text = st.text_area("問題文（必須）")
                col_img1, col_img2 = st.columns(2)
                q_img = col_img1.text_input("問題画像")
                a_img = col_img2.text_input("正答・解説画像")

                cols = st.columns(6)
                char_inputs = [
                    cols[i].text_input(
                        f"文字{i+1}", max_chars=1, key=f"c6_{i}"
                    )
                    for i in range(6)
                ]
                correct_word = st.text_input("正解（6文字）")
                exp_text = st.text_area("解説")

                if st.form_submit_button("🔤 6文字並べ替えを追加"):
                    if (
                        q_text
                        and all(char_inputs)
                        and len(correct_word) == 6
                    ):
                        new_item = {
                            "type": "6文字並べ替え",
                            "question": q_text,
                            "question_image": q_img,
                            "answer_image": a_img,
                            "image": q_img or a_img,
                            "option1": char_inputs[0],
                            "option2": char_inputs[1],
                            "option3": char_inputs[2],
                            "option4": char_inputs[3],
                            "option5": char_inputs[4],
                            "option6": char_inputs[5],
                            "answer": correct_word,
                            "explanation": exp_text,
                        }
                        st.session_state["added_data"] = pd.concat(
                            [
                                st.session_state["added_data"],
                                pd.DataFrame([new_item]),
                            ],
                            ignore_index=True,
                        )
                        st.success("6文字並べ替え問題を追加しました！")

        with add_tab_pair:
            st.markdown("##### 組み合わせクイズの追加")
            with st.form("form_pair", clear_on_submit=True):
                q_text = st.text_area("問題文（必須）")
                col_img1, col_img2 = st.columns(2)
                q_img = col_img1.text_input("問題画像")
                a_img = col_img2.text_input("正答・解説画像")

                p1_col1, p1_col2 = st.columns(2)
                l1, r1 = p1_col1.text_input("左 1"), p1_col2.text_input(
                    "右 1"
                )
                p2_col1, p2_col2 = st.columns(2)
                l2, r2 = p2_col1.text_input("左 2"), p2_col2.text_input(
                    "右 2"
                )
                p3_col1, p3_col2 = st.columns(2)
                l3, r3 = p3_col1.text_input("左 3"), p3_col2.text_input(
                    "右 3"
                )

                exp_text = st.text_area("解説")

                if st.form_submit_button("🔗 組み合わせを追加"):
                    if q_text and all([l1, r1, l2, r2, l3, r3]):
                        pair_ans = f"{l1}-{r1} / {l2}-{r2} / {l3}-{r3}"
                        new_item = {
                            "type": "組み合わせ",
                            "question": q_text,
                            "question_image": q_img,
                            "answer_image": a_img,
                            "image": q_img or a_img,
                            "left1": l1,
                            "right1": r1,
                            "left2": l2,
                            "right2": r2,
                            "left3": l3,
                            "right3": r3,
                            "answer": pair_ans,
                            "explanation": exp_text,
                        }
                        st.session_state["added_data"] = pd.concat(
                            [
                                st.session_state["added_data"],
                                pd.DataFrame([new_item]),
                            ],
                            ignore_index=True,
                        )
                        st.success("組み合わせ問題を追加しました！")

        with add_tab_free:
            st.markdown("##### 自由記述クイズの追加")
            with st.form("form_free", clear_on_submit=True):
                q_text = st.text_area("問題文（必須）")
                col_img1, col_img2 = st.columns(2)
                q_img = col_img1.text_input("問題画像")
                a_img = col_img2.text_input("正答・解説画像")

                ans_text = st.text_input("正解（「、」で複数可）")
                exp_text = st.text_area("解説")

                if st.form_submit_button("✏️ 自由記述を追加"):
                    if q_text and ans_text:
                        new_item = {
                            "type": "自由記述",
                            "question": q_text,
                            "question_image": q_img,
                            "answer_image": a_img,
                            "image": q_img or a_img,
                            "answer": ans_text,
                            "explanation": exp_text,
                        }
                        st.session_state["added_data"] = pd.concat(
                            [
                                st.session_state["added_data"],
                                pd.DataFrame([new_item]),
                            ],
                            ignore_index=True,
                        )
                        st.success("自由記述問題を追加しました！")

    elif tab_selection == "✏️ 2. データの編集・修正":
        st.subheader("🛠️ かんたん問題修正フォーム")

        if (
            "working_df" not in st.session_state
            or st.session_state["working_df"].empty
        ):
            with st.spinner("データを読み込み中..."):
                if (
                    "added_data" in st.session_state
                    and not st.session_state["added_data"].empty
                ):
                    merged = pd.concat(
                        [df_all, st.session_state["added_data"]],
                        ignore_index=True,
                    )
                else:
                    merged = df_all.copy()
                st.session_state["working_df"] = merged.reset_index(
                    drop=True
                )

        current_df = st.session_state["working_df"]

        if current_df.empty:
            st.info("編集対象のデータがありません。")
        else:
            st.markdown("##### 🔍 表示する問題を絞り込む")
            f_col1, f_col2, f_col3 = st.columns([2, 2, 3])

            story_col_name = None
            target_keywords = [
                "story",
                "編",
                "章",
                "chapter",
                "category",
                "カテゴリ",
                "arc",
                "エピソード",
                "シリーズ",
                "話",
            ]

            for col in current_df.columns:
                col_lower = str(col).lower().strip()
                if any(kw in col_lower for kw in target_keywords):
                    story_col_name = col
                    break

            story_options = ["すべて"]
            if story_col_name:
                unique_stories = current_df[story_col_name].dropna().unique()
                valid_stories = sorted(
                    [
                        str(s).strip()
                        for s in unique_stories
                        if str(s).strip()
                        and str(s).lower() not in ["nan", "none", "未設定", ""]
                    ]
                )
                story_options.extend(valid_stories)

            with f_col1:
                selected_story = st.selectbox(
                    "ストーリー（編）",
                    options=story_options,
                    key="filter_story",
                )
                if story_col_name:
                    st.caption(f"💡 検出された列名: `{story_col_name}`")
                else:
                    st.caption(
                        "⚠️ 該当するストーリー列が見つかりません"
                    )

            type_options = ["すべて"]
            if "type" in current_df.columns:
                unique_types = current_df["type"].dropna().unique()
                valid_types = sorted(
                    [
                        str(t).strip()
                        for t in unique_types
                        if str(t).strip()
                        and str(t).lower() not in ["nan", "none", ""]
                    ]
                )
                type_options.extend(valid_types)

            with f_col2:
                selected_type = st.selectbox(
                    "出題形式", options=type_options, key="filter_type"
                )

            init_kw = st.session_state.pop("edit_search_keyword", "")
            with f_col3:
                keyword = st.text_input(
                    "キーワード検索（問題文・解説等）",
                    value=init_kw,
                    placeholder="例：ルフィ、アラバスタ",
                )

            filtered_df = current_df.copy()

            if selected_story != "すべて" and story_col_name:
                filtered_df = filtered_df[
                    filtered_df[story_col_name].astype(str).str.strip()
                    == selected_story
                ]

            if selected_type != "すべて" and "type" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["type"].astype(str).str.strip()
                    == selected_type
                ]

            if keyword:
                mask = (
                    filtered_df.astype(str)
                    .apply(
                        lambda x: x.str.contains(
                            keyword, case=False, na=False
                        )
                    )
                    .any(axis=1)
                )
                filtered_df = filtered_df[mask]

            filtered_df = filtered_df.reset_index(drop=False)
            filtered_count = len(filtered_df)

            if filtered_count == 0:
                st.warning(
                    "条件に一致する問題が見つかりませんでした。フィルター条件を変更してください。"
                )
            else:
                if "edit_sub_idx" not in st.session_state:
                    st.session_state["edit_sub_idx"] = 0
                if st.session_state["edit_sub_idx"] >= filtered_count:
                    st.session_state["edit_sub_idx"] = 0

                st.write("---")

                nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])

                with nav_col1:
                    st.write("")
                    if st.button(
                        "◀ 前へ",
                        use_container_width=True,
                        disabled=(st.session_state["edit_sub_idx"] <= 0),
                    ):
                        st.session_state["edit_sub_idx"] -= 1
                        st.rerun()

                options_dict = {}
                for sub_i, r in filtered_df.iterrows():
                    orig_i = r["index"]
                    q_type = get_clean_str(r.get("type")) or "未設定"
                    q_txt = (
                        get_clean_str(r.get("question") or r.get("name"))
                        or "無題"
                    )
                    options_dict[
                        sub_i
                    ] = f"[{sub_i + 1}/{filtered_count}] (全{orig_i + 1}件目) 【{q_type}】 {q_txt[:25]}"

                with nav_col2:
                    current_idx_val = st.session_state["edit_sub_idx"]
                    selected_sub_idx = st.selectbox(
                        "問題を選択",
                        options=list(options_dict.keys()),
                        format_func=lambda x: options_dict[x],
                        index=current_idx_val,
                        key=f"select_box_sub_{current_idx_val}",
                    )

                    if selected_sub_idx != st.session_state["edit_sub_idx"]:
                        st.session_state["edit_sub_idx"] = selected_sub_idx
                        st.rerun()

                with nav_col3:
                    st.write("")
                    if st.button(
                        "次へ ▶",
                        use_container_width=True,
                        disabled=(
                            st.session_state["edit_sub_idx"]
                            >= filtered_count - 1
                        ),
                    ):
                        st.session_state["edit_sub_idx"] += 1
                        st.rerun()

                current_sub_idx = st.session_state["edit_sub_idx"]
                target_sub_row = filtered_df.iloc[current_sub_idx]
                selected_idx = target_sub_row["index"]
                target_row = current_df.iloc[selected_idx]

                st.markdown(
                    f"##### ✏️ 絞り込み問題 `{current_sub_idx + 1} / {filtered_count}` （全体データID: `{selected_idx + 1}`）の修正"
                )

                prev_col1, prev_col2 = st.columns(2)
                with prev_col1:
                    st.caption("🖼️ 現在の問題画像")
                    display_question_image(
                        target_row, width=200, show_caption=False
                    )
                with prev_col2:
                    q_val, a_val = format_question_and_answer(target_row)
                    st.caption("📝 現在の問題・解答")
                    st.write(f"**問題:** {q_val or '（なし）'}")
                    st.write(f"**正解:** {a_val or '（なし）'}")

                with st.form(f"quick_edit_form_{selected_idx}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        type_list = [
                            "キャラデータ",
                            "一問一答",
                            "一問多答",
                            "順序選択",
                            "6文字並べ替え",
                            "組み合わせ",
                            "自由記述",
                        ]
                        curr_type = get_clean_str(target_row.get("type"))
                        if curr_type and curr_type not in type_list:
                            type_list.append(curr_type)

                        type_idx = (
                            type_list.index(curr_type)
                            if curr_type in type_list
                            else 0
                        )
                        e_type = st.selectbox(
                            "出題種別 / タイプ",
                            options=type_list,
                            index=type_idx,
                        )

                        e_question = st.text_area(
                            "問題文 / 名前",
                            value=get_clean_str(
                                target_row.get("question")
                                or target_row.get("name")
                            ),
                            height=100,
                        )
                        e_q_img = st.text_input(
                            "問題画像（question_image）",
                            value=get_clean_str(
                                target_row.get("question_image")
                                or target_row.get("image")
                            ),
                        )
                        e_a_img = st.text_input(
                            "正答・解説画像（answer_image）",
                            value=get_clean_str(target_row.get("answer_image")),
                        )

                    with col_e2:
                        e_answer = st.text_input(
                            "正解（answer）",
                            value=get_clean_str(target_row.get("answer")),
                        )
                        e_opt1 = st.text_input(
                            "選択肢 1 / 左1",
                            value=get_clean_str(
                                target_row.get("option1")
                                or target_row.get("left1")
                            ),
                        )
                        e_opt2 = st.text_input(
                            "選択肢 2 / 右1",
                            value=get_clean_str(
                                target_row.get("option2")
                                or target_row.get("right1")
                            ),
                        )
                        e_opt3 = st.text_input(
                            "選択肢 3 / 左2",
                            value=get_clean_str(
                                target_row.get("option3")
                                or target_row.get("left2")
                            ),
                        )
                        e_opt4 = st.text_input(
                            "選択肢 4 / 右2",
                            value=get_clean_str(
                                target_row.get("option4")
                                or target_row.get("right4")
                            ),
                        )
                        e_exp = st.text_area(
                            "解説（explanation）",
                            value=get_clean_str(target_row.get("explanation")),
                            height=100,
                        )

                    submit_edit = st.form_submit_button(
                        "💾 修正内容を更新する", use_container_width=True
                    )

                    if submit_edit:
                        st.session_state["working_df"].at[
                            selected_idx, "type"
                        ] = e_type
                        if "question" in current_df.columns or e_question:
                            st.session_state["working_df"].at[
                                selected_idx, "question"
                            ] = e_question
                        st.session_state["working_df"].at[
                            selected_idx, "question_image"
                        ] = e_q_img
                        st.session_state["working_df"].at[
                            selected_idx, "answer_image"
                        ] = e_a_img
                        st.session_state["working_df"].at[
                            selected_idx, "image"
                        ] = (e_q_img or e_a_img)
                        st.session_state["working_df"].at[
                            selected_idx, "answer"
                        ] = e_answer
                        st.session_state["working_df"].at[
                            selected_idx, "explanation"
                        ] = e_exp

                        if "option1" in current_df.columns:
                            st.session_state["working_df"].at[
                                selected_idx, "option1"
                            ] = e_opt1
                        if "option2" in current_df.columns:
                            st.session_state["working_df"].at[
                                selected_idx, "option2"
                            ] = e_opt2
                        if "option3" in current_df.columns:
                            st.session_state["working_df"].at[
                                selected_idx, "option3"
                            ] = e_opt3
                        if "option4" in current_df.columns:
                            st.session_state["working_df"].at[
                                selected_idx, "option4"
                            ] = e_opt4

                        st.success(
                            f"✅ 全体ID `{selected_idx + 1}` の修正を保存しました！"
                        )
                        st.rerun()

            st.write("---")
            st.markdown("##### 📥 修正済みデータの書き出し")

            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                buffer_all = io.BytesIO()
                with pd.ExcelWriter(buffer_all, engine="openpyxl") as writer:
                    st.session_state["working_df"].to_excel(
                        writer, index=False
                    )

                st.download_button(
                    label="📥 修正済み全データをExcel出力 (`quiz_data_updated.xlsx`)",
                    data=buffer_all.getvalue(),
                    file_name="quiz_data_updated.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            with exp_col2:
                if st.button(
                    "🔄 修正を破棄して初期データに戻す",
                    use_container_width=True,
                ):
                    st.session_state["working_df"] = pd.DataFrame()
                    st.session_state["added_data"] = pd.DataFrame()
                    st.session_state["edit_sub_idx"] = 0
                    st.rerun()
