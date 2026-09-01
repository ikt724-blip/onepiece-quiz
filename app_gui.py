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


# 画像をBase64に変換（カスタムHTML/CSSアニメーション用）
def image_to_base64(img_path):
    try:
        with Image.open(img_path) as img:
            buffered = io.BytesIO()
            img_format = img.format if img.format else "PNG"
            img.save(buffered, format=img_format)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            mime_type = f"image/{img_format.lower()}"
            return f"data:{mime_type};base64,{img_str}"
    except Exception:
        return None


# --- 🖼️ 画像表示・フォルダ自動探索関数 ---
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
            q_text = str(row.get("question") or row.get("name") or "").strip()
            cap = f"画像 {idx + 1}" if not q_text else f"【画像 {idx + 1}】 {q_text[:20]}"

        if resolved_path:
            try:
                if resolved_path.startswith("http"):
                    st.image(resolved_path, caption=cap, width=width)
                else:
                    with Image.open(resolved_path) as img:
                        img_bytes = img.copy()
                        if width is None:
                            st.image(img_bytes, caption=cap, use_container_width="stretch")
                        else:
                            st.image(img_bytes, caption=cap, width=width)
            except Exception as e:
                st.warning(f"⚠️ 画像の表示エラー: {raw_path} ({e})")
        else:
            st.info(f"📷 画像ファイルが見つかりません: `{raw_path}`")


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


# 正解判定共通ロジック
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
    "🏴‍☠️ キャラクターデータ",
]

# --- サイドバーナビゲーション ---
with st.sidebar:
    st.header("🏴‍☠️ ナビセンター")

    if "current_nav" not in st.session_state:
        st.session_state["current_nav"] = menu_options[0]

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
            "flag",
        ],
        default_index=def_idx,
        key=f"nav_menu_main_{def_idx}",  # 👈 keyにdef_idxを含めることで外部からの変更を強制反映します
    )

    st.session_state["current_nav"] = selected

# 全データ取得
df_all = load_all_data()

# --- 1. ホーム画面 ---
if selected == "ホーム":
    import streamlit.components.v1 as components

    all_imgs = (
        glob.glob("images/*.png")
        + glob.glob("images/*.jpg")
        + glob.glob("images/*.jpeg")
        + glob.glob("*.png")
        + glob.glob("*.jpg")
    )

    wt100_full_html = ""

    if all_imgs:
        # 画面読み込みごとに自動で画像をランダム抽出（シャッフル）
        sample_imgs = random.sample(all_imgs, min(len(all_imgs), 60))
        
        NUM_COLS = 6
        columns_b64 = [[] for _ in range(NUM_COLS)]
        
        img_idx = 0
        for img_path in sample_imgs:
            if os.path.exists(img_path):
                b64_str = image_to_base64(img_path)
                if b64_str:
                    columns_b64[img_idx % NUM_COLS].append(b64_str)
                    img_idx += 1

        cols_html_list = []
        for i, col_imgs in enumerate(columns_b64):
            if not col_imgs:
                continue
            duplicated_imgs = col_imgs + col_imgs
            imgs_tags = "".join([f'<div class="img-box"><img src="{b64}" class="scroll-img" /></div>' for b64 in duplicated_imgs])
            
            col_class = "col-down" if i % 2 == 0 else "col-up"
            speed_class = f"speed-{(i % 3) + 1}"
            
            col_block = f'''
            <div class="scroll-column {col_class} {speed_class}">
                <div class="scroll-track">
                    {imgs_tags}
                </div>
            </div>
            '''
            cols_html_list.append(col_block)

        cols_html = "".join(cols_html_list)

        wt100_full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            width: 100%;
            height: 100%;
            background-color: #0e1117;
            font-family: sans-serif;
            overflow: hidden;
        }}

        .wt-hero-container {{
            position: relative;
            width: 100%;
            height: 600px;
            background-color: #000;
            overflow: hidden;
            border-radius: 12px;
        }}

        .scroll-wrapper {{
            display: flex;
            width: 100%;
            height: 100%;
            gap: 4px;
            opacity: 0.85;
            background-color: #000;
        }}

        .scroll-column {{
            flex: 1;
            height: 100%;
            overflow: hidden;
            position: relative;
        }}

        .scroll-track {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            width: 100%;
        }}

        .img-box {{
            width: 100%;
            height: 130px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #111;
            border-radius: 4px;
            overflow: hidden;
        }}

        .scroll-img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            display: block;
        }}

        @keyframes scrollDown {{
            0% {{ transform: translateY(-50%); }}
            100% {{ transform: translateY(0%); }}
        }}

        @keyframes scrollUp {{
            0% {{ transform: translateY(0%); }}
            100% {{ transform: translateY(-50%); }}
        }}

        .col-down .scroll-track {{ animation: scrollDown linear infinite; }}
        .col-up .scroll-track {{ animation: scrollUp linear infinite; }}

        .speed-1 .scroll-track {{ animation-duration: 22s; }}
        .speed-2 .scroll-track {{ animation-duration: 28s; }}
        .speed-3 .scroll-track {{ animation-duration: 34s; }}

        .wt-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10;
            pointer-events: none;
            background: radial-gradient(circle, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.85) 100%);
        }}

        .wt-title {{
            text-align: center;
            color: #fff;
            text-shadow: 0 4px 20px rgba(0,0,0,0.95), 0 0 25px rgba(255, 0, 0, 0.8);
        }}

        .wt-title h1 {{
            font-size: 2.6rem;
            font-weight: 900;
            margin: 0;
            letter-spacing: 2px;
            color: #ffffff;
        }}

        .wt-title p {{
            font-size: 1.1rem;
            color: #ff3b30;
            font-weight: bold;
            margin-top: 8px;
        }}
        </style>
        </head>
        <body>
            <div class="wt-hero-container">
                <div class="scroll-wrapper">
                    {cols_html}
                </div>
                <div class="wt-overlay">
                    <div class="wt-title">
                        <h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1>
                        <p>― 最強のデータベースを脳に刻め ―</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    if wt100_full_html:
        components.html(wt100_full_html, height=620)
    else:
        st.warning("表示できる画像ファイル（.png / .jpg）が見つかりません。")

    st.divider()
# --- 2. 練習モード ---
elif selected == "📖 練習モード":
    st.title("📖 練習モード")
    st.caption("自分のペースで苦手克服！出題条件を自由にカスタマイズして挑戦しましょう。")
    st.write("---")

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

        # ==========================================
        # 1. 練習開始前の設定画面（カードデザイン適用）
        # ==========================================
        if not st.session_state.practice_started:
            with st.container(border=True):
                # 上段：ダッシュボード風ステータス表示
                m_col1, m_col2 = st.columns([1, 2])
                with m_col1:
                    st.metric(label="📚 総問題数", value=f"{len(df_all):,} 問")
                with m_col2:
                    st.info("💡 **ヒント**: 条件を絞り込むことで、特定の分野や形式を集中して効率よく学習できます。", icon="ℹ️")

                st.divider()

                # 中段：条件設定フォーム
                st.markdown("##### ⚙️ 出題条件の設定")
                col1, col2 = st.columns(2)
                with col1:
                    num_q = st.number_input(
                        "🔢 出題数を選択",
                        min_value=1,
                        max_value=min(len(df_all), 100),
                        value=min(len(df_all), 10),
                        help="一度に挑戦する問題数を指定します。"
                    )
                with col2:
                    q_type_filter = st.selectbox(
                        "🏷️ 問題タイプ", 
                        ["すべて", "記述問題", "並び替え問題", "キャラマスター"],
                        help="特定の出題形式だけに絞り込むことができます。"
                    )

                st.write("") # スペース確保

                # 下段：メインアクションボタン（プライマリカラー＆フルサイズ）
                if st.button("🚀 練習を開始する", type="primary", use_container_width=True):
                    target_df = df_all.copy()
                    # 🚀 元のデータフレームでの行番号（ID）を記憶しておく
                    target_df["_original_index"] = target_df.index
                    
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

        # ==========================================
        # 2. 練習中の出題画面・結果表示
        # ==========================================
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

                if st.button("🔄 もう一度練習する", type="primary"):
                    st.session_state.practice_started = False
                    st.rerun()
            else:
                q = st.session_state.p_quiz_list[curr_idx]
                st.progress((curr_idx) / total_q)

                c_top1, c_top2 = st.columns([3, 1])
                with c_top1:
                    st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")
                
                # 🛠️ 修正箇所：ボタン遷移の連動処理を強化
                with c_top2:
                    if st.button("🛠️ この問題を修正する", key=f"btn_edit_q_{curr_idx}"):
                        # 1. 練習モードの実行状態を一旦リセット
                        st.session_state.practice_started = False
                        
                        # 2. 編集タブ（2番目）を開くフラグ
                        st.session_state["edit_active_tab"] = 1
                        
                        # 3. 編集対象のインデックスを確実に取得
                        target_id = q.get("_original_index")
                        if target_id is None:
                            target_id = q.get("index", curr_idx)
                        st.session_state["edit_target_index"] = target_id
                        
                        # 4. menu_optionsから正確な表記を検索して遷移先にセット
                        if "menu_options" in locals() or "menu_options" in globals():
                            for option in menu_options:
                                if "データ追加" in option or "編集" in option:
                                    st.session_state["current_nav"] = option
                                    break
                            else:
                                st.session_state["current_nav"] = "➕ データ追加・編集"
                        else:
                            st.session_state["current_nav"] = "➕ データ追加・編集"
                        
                        st.rerun()

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")

                is_char_q = "このキャラクターの名前は？" in question_text or bool(q.get("image") or q.get("画像"))
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

            if st.button("🔥 模試を開始する（タイマースタート）", use_container_width="stretch"):
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
                st.dataframe(pd.DataFrame(summary_data), use_container_width="stretch")

                if st.button("🔄 もう一度模試を受ける"):
                    st.session_state.exam_started = False
                    st.rerun()

            else:
                q = st.session_state.e_quiz_list[curr_idx]
                st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")

                is_char_q = "このキャラクターの名前は？" in question_text or bool(q.get("image") or q.get("画像"))
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
                            "回答して次の問題へ ➡", use_container_width="stretch"
                        )
                    with col_b2:
                        sub_skip = st.form_submit_button(
                            "スキップ", use_container_width="stretch"
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
    st.caption("〜 キャラクターマスタ＆問題データベース 爆速逆引き図鑑 〜")
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
            type_options = ["すべて"] + list(df_all["type"].dropna().unique()) if "type" in df_all.columns else ["すべて"]
            filter_type = st.selectbox("データ種別", type_options)
        with col_s3:
            filter_fruit = st.selectbox("悪魔の実", ["すべて", "能力者のみ", "非能力者"])

        filtered_df = df_all.copy()

        if search_query:
            mask = filtered_df.astype(str).apply(
                lambda x: x.str.contains(search_query, case=False, na=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]

        if filter_type != "すべて" and "type" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["type"] == filter_type]

        if filter_fruit != "すべて" and "devil_fruit" in filtered_df.columns:
            if filter_fruit == "能力者のみ":
                filtered_df = filtered_df[filtered_df["devil_fruit"].notna() & (filtered_df["devil_fruit"] != "")]
            elif filter_fruit == "非能力者":
                filtered_df = filtered_df[filtered_df["devil_fruit"].isna() | (filtered_df["devil_fruit"] == "")]

        filtered_df = filtered_df.reset_index(drop=True)

        if filtered_df.empty:
            st.warning("該当するデータが見つかりませんでした。")
        else:
            if "search_selected_index" not in st.session_state:
                st.session_state["search_selected_index"] = 0

            sel_idx = min(st.session_state["search_selected_index"], len(filtered_df) - 1)
            selected_item = filtered_df.iloc[sel_idx]

            c_name = get_clean_str(selected_item.get("name") or selected_item.get("名前")) or "詳細情報"
            c_id = get_clean_str(selected_item.get("characterid"))

            st.info(f"📌 **【選択中】: {c_name}** {f'(ID: {c_id})' if c_id else ''}")

            card_col1, card_col2 = st.columns([1, 2])
            with card_col1:
                display_question_image(selected_item, width=280, show_caption=True)
            with card_col2:
                name_val = get_clean_str(selected_item.get("name") or selected_item.get("名前"))
                if name_val:
                    st.markdown(f"### {name_val}")

                nick = get_clean_str(selected_item.get("nickname") or selected_item.get("異名"))
                if nick:
                    st.write(f"**異名/通り名:** {nick}")

                fruit = get_clean_str(selected_item.get("devil_fruit") or selected_item.get("悪魔の実"))
                if fruit:
                    st.write(f"**悪魔の実:** {fruit}")

                ftype = get_clean_str(selected_item.get("fruit_type"))
                if ftype:
                    st.write(f"**系統:** {ftype}")

                aff = get_clean_str(selected_item.get("affiliation") or selected_item.get("所属"))
                if aff:
                    st.write(f"**所属:** {aff}")

                q_text, a_text = format_question_and_answer(selected_item)
                if q_text and not name_val:
                    st.write(f"**問題:** {q_text}")
                    st.write(f"**正解:** {a_text}")

                exp = get_clean_str(selected_item.get("explanation") or selected_item.get("解説"))
                if exp:
                    st.write(f"**解説:** {exp}")

                if st.button("🛠️ このデータを編集・修正する", use_container_width=True):
                    target_kw = name_val or get_clean_str(selected_item.get("image") or selected_item.get("画像")) or q_text
                    st.session_state["edit_search_keyword"] = target_kw
                    st.session_state["edit_active_tab"] = 1
                    st.session_state["current_nav"] = "➕ データ追加・編集"
                    st.rerun()

            st.write("")
            st.caption(f"💡 表の行を選択すると、詳細プレビューが更新されます。（該当件数: {len(filtered_df)} 件）")

            search_event = st.dataframe(
                filtered_df,
                on_select="rerun",
                selection_mode="single-row",
                use_container_width=True,
                key="df_search_select"
            )

            if search_event and hasattr(search_event, "selection") and search_event.selection.get("rows"):
                picked_row = search_event.selection["rows"][0]
                if picked_row != st.session_state["search_selected_index"]:
                    st.session_state["search_selected_index"] = picked_row
                    st.rerun()

# --- 6. データ追加・編集 ---
elif selected == "➕ データ追加・編集":
    st.title("➕ データ追加・編集")

    # 他のページ（練習モード等）から遷移してきた際の活性化タブ判定
    default_tab_idx = st.session_state.get("edit_active_tab", 0)

    # タブの作成（ラジオボタンによる切替）
    tab_titles = ["📝 1. データの新規追加", "✏️ 2. データの編集・削除"]
    
    # default_tab_idx が範囲外にならないよう制御
    if default_tab_idx >= len(tab_titles):
        default_tab_idx = 0

    tab_selection = st.radio(
        "操作を選択してください",
        tab_titles,
        index=default_tab_idx,
        horizontal=True,
        key="data_edit_tab_radio"
    )

    # --- 1. 新規追加タブ ---
    if tab_selection == "📝 1. データの新規追加":
        st.subheader("📝 新しい問題データの追加")
        # （既存の新規追加フォームコードをここに配置）
        st.info("ここに新規問題追加用のフォームが入ります。")

    # --- 2. 編集・削除タブ ---
    elif tab_selection == "✏️ 2. データの編集・削除":
        st.subheader("🛠️ かんたん問題修正・削除フォーム")

        if "working_df" not in st.session_state or st.session_state["working_df"].empty:
            st.session_state["working_df"] = df_all.copy().reset_index(drop=True)

        current_df = st.session_state["working_df"]

        if current_df.empty:
            st.info("編集対象のデータがありません。")
        else:
            # 🚀 練習モードや他ページからのダイレクト割り込み処理
            target_idx = None
            if "target_edit_global_index" in st.session_state:
                target_idx = st.session_state.pop("target_edit_global_index")
            elif "edit_target_index" in st.session_state:
                target_idx = st.session_state.pop("edit_target_index")

            # 強制指定の初期位置用フラグ
            forced_select_pos = None

            if target_idx is not None:
                try:
                    target_idx = int(target_idx)
                    if 0 <= target_idx < len(current_df):
                        # フィルターをクリア
                        st.session_state["filter_story"] = "すべて"
                        st.session_state["filter_type"] = "すべて"
                        st.session_state["filter_keyword"] = ""
                        forced_select_pos = target_idx
                except (ValueError, TypeError):
                    pass

            # キャラ名鑑等からのキーワード連携対応
            if "edit_search_keyword" in st.session_state and st.session_state["edit_search_keyword"]:
                st.session_state["filter_keyword"] = st.session_state.pop("edit_search_keyword")
                st.session_state["filter_story"] = "すべて"
                st.session_state["filter_type"] = "すべて"

            st.markdown("##### 🔍 表示する問題を絞り込む")
            f_col1, f_col2, f_col3 = st.columns([2, 2, 3])

            story_col_name = None
            target_keywords = ["story", "編", "章", "chapter", "category", "カテゴリ", "arc", "エピソード"]
            
            for col in current_df.columns:
                if any(kw in str(col).lower() for kw in target_keywords):
                    story_col_name = col
                    break

            story_options = ["すべて"]
            if story_col_name:
                unique_stories = current_df[story_col_name].dropna().unique()
                valid_stories = sorted([str(s).strip() for s in unique_stories if str(s).strip()])
                story_options.extend(valid_stories)

            with f_col1:
                selected_story = st.selectbox("ストーリー（編）", options=story_options, key="filter_story")

            type_options = ["すべて"]
            if "type" in current_df.columns:
                unique_types = current_df["type"].dropna().unique()
                valid_types = sorted([str(t).strip() for t in unique_types if str(t).strip()])
                type_options.extend(valid_types)

            with f_col2:
                selected_type = st.selectbox("出題形式", options=type_options, key="filter_type")

            with f_col3:
                keyword = st.text_input("キーワード検索", placeholder="問題文や解答で検索", key="filter_keyword")

            # フィルタリング適用
            filtered_df = current_df.copy()
            # 元の作業DF内の絶対行番号を保持する別名カラムを付与
            filtered_df["_orig_row_id"] = current_df.index

            if selected_story != "すべて" and story_col_name:
                filtered_df = filtered_df[filtered_df[story_col_name].astype(str).str.strip() == selected_story]
            if selected_type != "すべて" and "type" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["type"].astype(str).str.strip() == selected_type]
            if keyword:
                mask = filtered_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False, na=False)).any(axis=1)
                filtered_df = filtered_df[mask]

            filtered_count = len(filtered_df)

            if filtered_count == 0:
                st.warning("条件に一致する問題が見つかりませんでした。")
            else:
                # 選択位置の決定
                default_pos = 0
                if forced_select_pos is not None:
                    # 割り込み指定されたIDが絞り込み結果内の何番目にあるか探す
                    matched_positions = [pos for pos, orig_id in enumerate(filtered_df["_orig_row_id"]) if orig_id == forced_select_pos]
                    if matched_positions:
                        default_pos = matched_positions[0]

                # 表示用ラベル生成関数
                def make_label(i):
                    row = filtered_df.iloc[i]
                    orig_num = row["_orig_row_id"] + 1
                    q_text = get_clean_str(row.get("question") or row.get("name") or row.get("問題") or "")
                    if not q_text:
                        q_text = "（問題文なし）"
                    return f"【No.{orig_num}】 {q_text[:35]}..."

                # セレクトボックス（keyの衝突を防ぐため index 引数で安全制御）
                selected_pos = st.selectbox(
                    f"編集・削除する問題を選択（全 {filtered_count} 件）",
                    options=list(range(filtered_count)),
                    index=default_pos if default_pos < filtered_count else 0,
                    format_func=make_label,
                    key="edit_select_pos_key"
                )

                selected_row = filtered_df.iloc[selected_pos]
                orig_index = int(selected_row["_orig_row_id"])

                st.markdown("---")
                st.markdown(f"#### ✏️ 問題 No.{orig_index + 1} の編集・削除")

                # 編集フォーム
                with st.form(key=f"edit_form_{orig_index}"):
                    edited_data = {}
                    for col in current_df.columns:
                        if col in ["_global_index", "_orig_row_id"]:
                            continue
                        val = selected_row.get(col, "")
                        val_str = "" if pd.isna(val) else str(val)
                        
                        if col in ["question", "explanation", "問題", "解説"]:
                            edited_data[col] = st.text_area(f"【{col}】", value=val_str)
                        else:
                            edited_data[col] = st.text_input(f"【{col}】", value=val_str)

                    if st.form_submit_button("💾 変更を保存する", use_container_width=True):
                        for col, new_val in edited_data.items():
                            st.session_state["working_df"].at[orig_index, col] = new_val
                        st.success(f"問題 No.{orig_index + 1} の更新を保存しました！")
                        st.rerun()

                # --- 🗑️ 問題の削除処理エリア ---
                with st.expander("🗑️ この問題を削除する（危険エリア）"):
                    st.warning("この操作を実行すると、作業データから問題が取り除かれます。")
                    confirm_delete = st.checkbox("本当に削除してよろしければチェックを入れてください", key=f"chk_del_{orig_index}")
                    
                    if st.button("🚨 問題を完全に削除", type="primary", disabled=not confirm_delete, key=f"btn_del_{orig_index}"):
                        st.session_state["working_df"] = st.session_state["working_df"].drop(index=orig_index).reset_index(drop=True)
                        st.success(f"問題 No.{orig_index + 1} を削除しました。")
                        st.rerun()

# --- 7. キャラクターデータモード ---
elif selected == "🏴 キャラクターデータ":
    st.title("🏴 キャラクター名鑑")
    st.caption("登録されているキャラクターの一覧・詳細情報を閲覧できます。")
    st.write("---")

    if "working_df" in st.session_state and not st.session_state["working_df"].empty:
        base_df = st.session_state["working_df"]
    elif "df_all" in globals() and isinstance(df_all, pd.DataFrame):
        base_df = df_all.copy()
    else:
        base_df = pd.DataFrame()

    if not base_df.empty and "type" in base_df.columns:
        char_df = base_df[base_df["type"].astype(str).str.strip() == "キャラデータ"].copy()
    else:
        char_df = pd.DataFrame()

    if char_df.empty:
        st.info("登録されているキャラクターデータがありません。「➕ データ追加・編集」タブからキャラデータを追加してください。")
    else:
        c_search1, c_search2 = st.columns([2, 1])
        with c_search1:
            search_kw = st.text_input("🔍 キャラクター検索（名前・異名・所属など）", placeholder="例: ルフィ、麦わら")
        
        with c_search2:
            ftype_options = ["すべて"]
            if "fruit_type" in char_df.columns:
                valid_types = sorted([str(x).strip() for x in char_df["fruit_type"].dropna().unique() if str(x).strip()])
                ftype_options.extend(valid_types)
            selected_ftype = st.selectbox("悪魔の実の系統", options=ftype_options)

        filtered_char = char_df.copy()
        if search_kw:
            mask = filtered_char.astype(str).apply(lambda x: x.str.contains(search_kw, case=False, na=False)).any(axis=1)
            filtered_char = filtered_char[mask]
        if selected_ftype != "すべて" and "fruit_type" in filtered_char.columns:
            filtered_char = filtered_char[filtered_char["fruit_type"].astype(str).str.strip() == selected_ftype]

        st.write(f"該当件数: **{len(filtered_char)}** 件")
        st.write("---")

        cols = st.columns(3)
        for idx, (_, row) in enumerate(filtered_char.iterrows()):
            with cols[idx % 3]:
                with st.container(border=True):
                    img_val = get_clean_str(row.get("image") or row.get("question_image"))
                    if img_val:
                        st.image(img_val, use_container_width=True)
                    else:
                        st.caption("🖼️ No Image")

                    c_name = get_clean_str(row.get("name") or row.get("question")) or "名称未設定"
                    c_nick = get_clean_str(row.get("nickname"))
                    c_fruit = get_clean_str(row.get("devil_fruit"))
                    c_ftype = get_clean_str(row.get("fruit_type"))
                    c_aff = get_clean_str(row.get("affiliation"))

                    st.markdown(f"### {c_name}")
                    if c_nick:
                        st.caption(f"【異名】{c_nick}")
                    
                    st.write("---")
                    st.write(f"**所属:** {c_aff or '不明'}")
                    st.write(f"**悪魔の実:** {c_fruit or 'なし'}")
                    if c_ftype:
                        st.write(f"**系統:** {c_ftype}")

                    if st.button("✏️ 編集", key=f"btn_edit_char_{idx}", use_container_width=True):
                        st.session_state["edit_search_keyword"] = c_name
                        st.session_state["edit_active_tab"] = 1
                        st.session_state["current_nav"] = "➕ データ追加・編集"
                        st.rerun()
