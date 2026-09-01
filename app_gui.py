import base64
import glob
import io
import os
import random
import re
import time
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_option_menu import option_menu

# --- ページ基本設定 ---
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策", page_icon="🏴‍☠️", layout="wide"
)

# --- 1. データ読み込み＆セッション状態管理 ---
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

    return pd.concat(df_list, ignore_index=True)

df_all = load_all_data()

# アプリ全体で共有する「作業用データフレーム」の初期化
if "working_df" not in st.session_state or st.session_state["working_df"].empty:
    st.session_state["working_df"] = df_all.copy().reset_index(drop=True)

# 苦手問題管理用のリスト（間違えた問題のインデックスを保持）
if "wrong_q_indices" not in st.session_state:
    st.session_state["wrong_q_indices"] = set()

# 共通ヘルパー関数
def get_clean_str(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ["nan", "none", "<na>"]:
        return ""
    return s

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

def display_question_image(row, width=200, show_caption=True):
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
        return

    for idx, raw_path in enumerate(img_sources):
        resolved_path = None
        if raw_path.startswith("http://") or raw_path.startswith("https://") or raw_path.startswith("data:image"):
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
                st.image(resolved_path, caption=cap, width=width)
            except Exception:
                pass

def get_correct_answers_list(q, correct_ans_str):
    answers = []
    for i in range(1, 10):
        val = get_clean_str(q.get(f"answer_{i}"))
        if val:
            answers.append(val)
            
    if not answers and correct_ans_str:
        if "、" in correct_ans_str or "," in correct_ans_str:
            answers = [t.strip() for t in re.split(r"[、,]", correct_ans_str) if t.strip()]
        else:
            answers = [correct_ans_str.strip()]
            
    return answers

def check_answers_multi(user_inputs, correct_answers):
    user_clean = [str(u).strip() for u in user_inputs if str(u).strip()]
    correct_clean = [str(c).strip() for c in correct_answers if str(c).strip()]
    if not user_clean or len(user_clean) != len(correct_clean):
        return False
    return set(user_clean) == set(correct_clean)

def format_question_and_answer(q):
    raw_question = get_clean_str(q.get("question") or q.get("問題") or q.get("Question") or q.get("question_text"))
    name = get_clean_str(q.get("name") or q.get("名前") or q.get("キャラ名") or q.get("Name"))
    image = get_clean_str(q.get("image") or q.get("画像"))
    devil_fruit = get_clean_str(q.get("devil_fruit") or q.get("悪魔の実") or q.get("能力"))
    affiliation = get_clean_str(q.get("affiliation") or q.get("所属") or q.get("組織"))
    nickname = get_clean_str(q.get("nickname") or q.get("異名") or q.get("通り名"))

    if raw_question:
        ans = get_clean_str(q.get("answer") or q.get("解答") or q.get("正解") or devil_fruit or name)
        return raw_question, ans
    if image and name: return "このキャラクターの名前は？", name
    if devil_fruit and name: return f"「{name}」が食べた悪魔の実の名称は？", devil_fruit
    if affiliation and name: return f"「{name}」の主な所属（組織・海賊団など）は？", affiliation
    if nickname and name: return f"「{name}」の異名（通り名）は？", nickname
    if name: return "このキャラクターの名前は？", name
    return "このキャラクターの名前は？", name

# --- 2. サイドバーナビゲーション ---
menu_options = [
    "ホーム",
    "練習モード",
    "本番模試",
    "苦手克服",
    "AI検索",
    "データ編集",
    "キャラ名鑑",
]

if "current_nav" not in st.session_state:
    st.session_state["current_nav"] = menu_options[0]

with st.sidebar:
    st.header("🏴‍☠️ ナビセンター")
    def_idx = menu_options.index(st.session_state["current_nav"]) if st.session_state["current_nav"] in menu_options else 0

    selected = option_menu(
        menu_title=None,
        options=menu_options,
        icons=["house", "book", "trophy", "fire", "search", "pencil", "person"],
        default_index=def_idx,
        key="main_menu_nav"
    )
    
    st.session_state["current_nav"] = selected

current_data = st.session_state.get("working_df", pd.DataFrame())

# --- 画面制御 ---
if selected == "ホーム":
    render_home_hero()

elif selected == "練習モード":
    st.title("📖 練習モード")
    st.write("ここは練習モードです。")

elif selected == "本番模試":
    st.title("🏆 本番模試 (50問 / 60分)")
    st.caption("全データからランダムで50問出題されます。")
    st.write("---")

    if current_data.empty:
        st.warning("⚠️ 出題できるデータが読み込まれていません。Excelファイルを確認してください。")
    else:
        if "exam_started" not in st.session_state:
            st.session_state.exam_started = False
        if "e_curr_idx" not in st.session_state:
            st.session_state.e_curr_idx = 0
        if "e_quiz_list" not in st.session_state:
            st.session_state.e_quiz_list = []
        if "e_user_answers" not in st.session_state:
            st.session_state.e_user_answers = {}

        if not st.session_state.exam_started:
            st.info(f"📚 現在の総問題数: **{len(current_data)} 問**")
            if st.button("🔥 模試を開始する", type="primary", use_container_width=True):
                target_df = current_data.copy()
                target_df["_original_index"] = target_df.index
                num_questions = min(50, len(target_df))
                shuffled = target_df.sample(n=num_questions).reset_index(drop=True)
                
                st.session_state.e_quiz_list = shuffled.to_dict("records")
                st.session_state.e_curr_idx = 0
                st.session_state.e_user_answers = {}
                st.session_state.exam_started = True
                st.rerun()

        else:
            total_q = len(st.session_state.e_quiz_list)
            curr_idx = st.session_state.e_curr_idx

            if curr_idx >= total_q:
                st.balloons()
                st.markdown("## 🏁 模試終了！ 結果発表")
                
                score = 0
                summary_data = []
                for idx, q_item in enumerate(st.session_state.e_quiz_list):
                    q_txt, c_ans_raw = format_question_and_answer(q_item)
                    correct_list = get_correct_answers_list(q_item, c_ans_raw)
                    u_ans = st.session_state.e_user_answers.get(idx, "")
                    
                    is_c = check_answers_multi([u_ans], correct_list)
                    orig_idx = q_item.get("_original_index")
                    
                    if is_c:
                        score += 1
                        if orig_idx is not None:
                            st.session_state["wrong_q_indices"].discard(orig_idx)
                    else:
                        if orig_idx is not None:
                            st.session_state["wrong_q_indices"].add(orig_idx)

                    summary_data.append({
                        "問": idx + 1,
                        "問題文": q_txt,
                        "あなたの解答": u_ans,
                        "正解": "、".join(correct_list),
                        "判定": "⭕ 正解" if is_c else "❌ 不正解"
                    })

                st.markdown(f"### 最終得点: **{score} / {total_q} 問**")
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

                if st.button("🔄 もう一度模試を受ける", type="primary"):
                    st.session_state.exam_started = False
                    st.rerun()

            else:
                st.progress((curr_idx) / total_q)
                q = st.session_state.e_quiz_list[curr_idx]
                st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")
                
                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")
                display_question_image(q, show_caption=False)

                with st.form(f"exam_form_{curr_idx}"):
                    curr_input = st.text_input("解答を入力", key=f"e_ans_{curr_idx}")
                    sub_next = st.form_submit_button("回答して次の問題へ ➡", use_container_width=True)

                if sub_next:
                    st.session_state.e_user_answers[curr_idx] = curr_input
                    st.session_state.e_curr_idx += 1
                    st.rerun()


elif selected == "AI検索":
    st.title("🔍 AI検索モード")
    st.caption("キーワードで問題やキャラクター情報を瞬時に一括検索できます。")
    st.write("---")

    if current_data.empty:
        st.warning("⚠️ 検索対象のデータが読み込まれていません。")
    else:
        search_query = st.text_input("🔍 キーワードを入力（例: ルフィ、ゴムゴム、アラバスタ）", "")
        
        filtered_df = current_data.copy()
        if search_query.strip():
            mask = filtered_df.astype(str).apply(
                lambda x: x.str.contains(search_query.strip(), case=False, na=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]

        st.markdown(f"検索結果: **{len(filtered_df)}** 件")
        st.dataframe(filtered_df, use_container_width=True)


elif selected == "苦手克服":
    st.title("🔥 苦手克服モード")
    st.caption("練習モードや本番模試で間違えた問題だけを集中して復習できます。")
    st.write("---")

    wrong_indices = list(st.session_state.get("wrong_q_indices", set()))
    
    if not wrong_indices:
        st.success("🎉 現在、登録されている苦手問題はありません！順調なペースです。")
    else:
        st.warning(f"現在 **{len(wrong_indices)} 問** の苦手問題が記録されています。")
        
        if "review_started" not in st.session_state:
            st.session_state.review_started = False
        if "r_curr_idx" not in st.session_state:
            st.session_state.r_curr_idx = 0
        if "r_quiz_list" not in st.session_state:
            st.session_state.r_quiz_list = []

        if not st.session_state.review_started:
            if st.button("🔥 苦手問題の復習を開始する", type="primary", use_container_width=True):
                wrong_df = current_data.iloc[wrong_indices].copy()
                wrong_df["_original_index"] = wrong_df.index
                st.session_state.r_quiz_list = wrong_df.to_dict("records")
                st.session_state.r_curr_idx = 0
                st.session_state.review_started = True
                st.rerun()
        else:
            total_q = len(st.session_state.r_quiz_list)
            curr_idx = st.session_state.r_curr_idx

            if curr_idx >= total_q:
                st.balloons()
                st.markdown("## 🎉 苦手克服トレーニング完了！")
                if st.button("🔄 モード選択へ戻る", type="primary"):
                    st.session_state.review_started = False
                    st.rerun()
            else:
                q = st.session_state.r_quiz_list[curr_idx]
                st.progress((curr_idx) / total_q)
                st.markdown(f"### 苦手復習 第 {curr_idx + 1} 問 / 全 {total_q} 問")

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")
                display_question_image(q, show_caption=False)

                correct_list = get_correct_answers_list(q, correct_ans_raw)

                with st.form(f"review_form_{curr_idx}"):
                    u_input = st.text_input("解答を入力", key=f"r_ans_{curr_idx}")
                    sub_rev = st.form_submit_button("回答する", use_container_width=True)

                if sub_rev:
                    is_correct = check_answers_multi([u_input], correct_list)
                    disp_ans = "、".join(correct_list)
                    orig_idx = q.get("_original_index")
                    
                    if is_correct:
                        st.success("⭕ 正解！苦手リストから解除されました。")
                        if orig_idx is not None:
                            st.session_state["wrong_q_indices"].discard(orig_idx)
                    else:
                        st.error(f"❌ 不正解... 正解は: **{disp_ans}**")

                    exp = get_clean_str(q.get("explanation") or q.get("解説"))
                    if exp:
                        st.caption(f"💡 【解説】: {exp}")
                    
                    st.session_state.r_curr_idx += 1
                    st.button("次の問題へ ➡")


elif selected == "データ編集":
    st.title("✏️ データ追加・編集")
    st.caption("問題データの新規追加や修正を行えます。")
    st.write("---")

    if current_data.empty:
        st.warning("⚠️ データが見つかりません。")
    else:
        st.subheader("データ一覧")
        st.dataframe(current_data, use_container_width=True)


elif selected == "キャラ名鑑":
    st.title("🏴 キャラクター名鑑")
    st.caption("登録されている全キャラクターをカード形式で一覧表示します。")
    st.write("---")

    if current_data.empty:
        st.warning("⚠️ 表示できるキャラデータがありません。")
    else:
        search_kw = st.text_input("🔍 キャラクター検索", "", placeholder="名前、異名、所属などで絞り込み")
        char_df = current_data.copy()

        if search_kw.strip():
            mask = char_df.astype(str).apply(lambda x: x.str.contains(search_kw.strip(), case=False, na=False)).any(axis=1)
            char_df = char_df[mask]

        st.caption(f"該当件数: **{len(char_df)}** 件")
        
        cols = st.columns(3)
        for idx, (_, row) in enumerate(char_df.head(60).iterrows()):
            c_name = get_clean_str(row.get("name") or row.get("名前") or row.get("question") or f"No.{idx + 1}")
            c_nick = get_clean_str(row.get("nickname") or row.get("異名"))
            c_img = get_clean_str(row.get("image") or row.get("画像"))
            c_aff = get_clean_str(row.get("affiliation") or row.get("所属"))
            c_fruit = get_clean_str(row.get("devil_fruit") or row.get("悪魔の実") or row.get("answer"))

            with cols[idx % 3]:
                with st.container(border=True):
                    if c_img:
                        st.image(c_img, use_container_width=True)
                    st.markdown(f"**{c_name}**")
                    if c_nick:
                        st.caption(f"【{c_nick}】")
                    if c_aff:
                        st.caption(f"🏴 {c_aff}")
                    if c_fruit:
                        st.caption(f"🍈 {c_fruit}")

# --- 3. ホーム画面 ---
if selected == "ホーム":
    import streamlit.components.v1 as components
    all_imgs = glob.glob("images/*.png") + glob.glob("images/*.jpg") + glob.glob("images/*.jpeg") + glob.glob("*.png") + glob.glob("*.jpg")
    wt100_full_html = ""

    if all_imgs:
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
            if not col_imgs: continue
            duplicated_imgs = col_imgs + col_imgs
            imgs_tags = "".join([f'<div class="img-box"><img src="{b64}" class="scroll-img" /></div>' for b64 in duplicated_imgs])
            col_class = "col-down" if i % 2 == 0 else "col-up"
            speed_class = f"speed-{(i % 3) + 1}"
            cols_html_list.append(f'<div class="scroll-column {col_class} {speed_class}"><div class="scroll-track">{imgs_tags}</div></div>')

        wt100_full_html = f"""
        <!DOCTYPE html><html><head><style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{ width: 100%; height: 100%; background-color: #0e1117; font-family: sans-serif; overflow: hidden; }}
        .wt-hero-container {{ position: relative; width: 100%; height: 600px; background-color: #000; overflow: hidden; border-radius: 12px; }}
        .scroll-wrapper {{ display: flex; width: 100%; height: 100%; gap: 4px; opacity: 0.85; background-color: #000; }}
        .scroll-column {{ flex: 1; height: 100%; overflow: hidden; position: relative; }}
        .scroll-track {{ display: flex; flex-direction: column; gap: 6px; width: 100%; }}
        .img-box {{ width: 100%; height: 130px; display: flex; align-items: center; justify-content: center; background-color: #111; border-radius: 4px; overflow: hidden; }}
        .scroll-img {{ max-width: 100%; max-height: 100%; object-fit: contain; display: block; }}
        @keyframes scrollDown {{ 0% {{ transform: translateY(-50%); }} 100% {{ transform: translateY(0%); }} }}
        @keyframes scrollUp {{ 0% {{ transform: translateY(0%); }} 100% {{ transform: translateY(-50%); }} }}
        .col-down .scroll-track {{ animation: scrollDown linear infinite; }}
        .col-up .scroll-track {{ animation: scrollUp linear infinite; }}
        .speed-1 .scroll-track {{ animation-duration: 22s; }}
        .speed-2 .scroll-track {{ animation-duration: 28s; }}
        .speed-3 .scroll-track {{ animation-duration: 34s; }}
        .wt-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 10; pointer-events: none; background: radial-gradient(circle, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.85) 100%); }}
        .wt-title {{ text-align: center; color: #fff; text-shadow: 0 4px 20px rgba(0,0,0,0.95), 0 0 25px rgba(255, 0, 0, 0.8); }}
        .wt-title h1 {{ font-size: 2.6rem; font-weight: 900; margin: 0; letter-spacing: 2px; color: #ffffff; }}
        .wt-title p {{ font-size: 1.1rem; color: #ff3b30; font-weight: bold; margin-top: 8px; }}
        </style></head><body>
            <div class="wt-hero-container">
                <div class="scroll-wrapper">{"".join(cols_html_list)}</div>
                <div class="wt-overlay"><div class="wt-title"><h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1><p>― 最強のデータベースを脳に刻め ―</p></div></div>
            </div>
        </body></html>
        """

    if wt100_full_html:
        components.html(wt100_full_html, height=620)
    else:
        st.warning("表示できる画像ファイルが見つかりません。")

# --- 4. 練習モード ---
elif selected == "練習モード":
    st.title("📖 練習モード")
    st.caption("自分のペースで苦手克服！出題条件を自由にカスタマイズして挑戦しましょう。")
    st.write("---")

    if current_data.empty:
        st.warning("出題できるデータが見つかりません。")
    else:
        if "practice_started" not in st.session_state: st.session_state.practice_started = False
        if "p_curr_idx" not in st.session_state: st.session_state.p_curr_idx = 0
        if "p_quiz_list" not in st.session_state: st.session_state.p_quiz_list = []
        if "p_score" not in st.session_state: st.session_state.p_score = 0
        if "p_user_answers" not in st.session_state: st.session_state.p_user_answers = []

        if not st.session_state.practice_started:
            with st.container(border=True):
                m_col1, m_col2 = st.columns([1, 2])
                with m_col1: st.metric(label="📚 総問題数", value=f"{len(current_data):,} 問")
                with m_col2: st.info("💡 条件を絞り込むことで、特定の分野や形式を集中して効率よく学習できます。")
                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    num_q = st.number_input("🔢 出題数を選択", min_value=1, max_value=max(1, len(current_data)), value=min(len(current_data), 10))
                with col2:
                    q_type_filter = st.selectbox("🏷️ 問題タイプ", ["すべて", "一問一答", "一問多答", "順序選択", "6文字並べ替え", "自由記述"])

                if st.button("🚀 練習を開始する", type="primary", use_container_width=True):
                    target_df = current_data.copy()
                    target_df["_original_index"] = target_df.index
                    if q_type_filter != "すべて" and "type" in target_df.columns:
                        target_df = target_df[target_df["type"] == q_type_filter]
                    if target_df.empty: target_df = current_data.copy()

                    shuffled = target_df.sample(n=min(num_q, len(target_df))).reset_index(drop=True)
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
                st.markdown(f"## 🎉 練習終了！\n### 結果: **{total_q}** 問中 **{st.session_state.p_score}** 問正解！")
                res_df = pd.DataFrame(st.session_state.p_user_answers)
                if not res_df.empty: st.dataframe(res_df, use_container_width=True)
                if st.button("🔄 もう一度練習する", type="primary"):
                    st.session_state.practice_started = False
                    st.rerun()
            else:
                q = st.session_state.p_quiz_list[curr_idx]
                st.progress((curr_idx) / total_q)
                c_top1, c_top2 = st.columns([3, 1])
                with c_top1: st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")
                with c_top2:
                    if st.button("🛠️ この問題を修正する", key=f"btn_edit_q_{curr_idx}"):
                        st.session_state.practice_started = False
                        st.session_state["target_edit_global_index"] = q.get("_original_index", curr_idx)
                        st.session_state["edit_active_tab"] = 1
                        st.session_state["data_edit_tab_radio"] = "✏️ 2. データの編集・削除"
                        st.session_state["current_nav"] = "データ追加・編集"
                        st.rerun()

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")
                display_question_image(q, show_caption=False)

                correct_list = get_correct_answers_list(q, correct_ans_raw)
                num_inputs = len(correct_list)

                with st.form(f"practice_form_{curr_idx}"):
                    user_inputs = []
                    if num_inputs > 1:
                        for i in range(num_inputs):
                            user_inputs.append(st.text_input(f"解答 {i+1}", key=f"p_ans_{curr_idx}_{i}"))
                    else:
                        user_inputs.append(st.text_input("解答を入力", key=f"p_ans_{curr_idx}_0"))

                    sub_c1, sub_c2 = st.columns(2)
                    submitted = sub_c1.form_submit_button("回答する", use_container_width=True)
                    passed = sub_c2.form_submit_button("パス", use_container_width=True)

                if submitted:
                    is_correct = check_answers_multi(user_inputs, correct_list)
                    disp_ans = "、".join(correct_list)
                    orig_idx = q.get("_original_index")
                    if is_correct:
                        st.success("⭕ 正解！")
                        st.session_state.p_score += 1
                        if orig_idx is not None: st.session_state["wrong_q_indices"].discard(orig_idx)
                    else:
                        st.error(f"❌ 不正解... 正解は: **{disp_ans}**")
                        if orig_idx is not None: st.session_state["wrong_q_indices"].add(orig_idx)

                    exp = get_clean_str(q.get("explanation") or q.get("解説"))
                    if exp: st.caption(f"💡 【解説】: {exp}")
                    st.session_state.p_user_answers.append({"問題": question_text, "あなたの解答": "、".join(user_inputs), "正解": disp_ans, "判定": "⭕ 正解" if is_correct else "❌ 不正解"})
                    st.session_state.p_curr_idx += 1
                    st.button("次の問題へ ➡")
                elif passed:
                    st.session_state.p_curr_idx += 1
                    st.rerun()

# --- 5. 本番模試 ---
elif selected == "本番模試 (50問/60分)":
    st.title("🏆 本番模試（50問 / 60分）")
    st.caption("本番同様の制限時間で挑戦！全データからランダム出題されます。")
    st.write("---")

    if current_data.empty:
        st.warning("出題できるデータが見つかりません。")
    else:
        if "exam_started" not in st.session_state: st.session_state.exam_started = False
        if "exam_start_time" not in st.session_state: st.session_state.exam_start_time = 0
        if "e_curr_idx" not in st.session_state: st.session_state.e_curr_idx = 0
        if "e_quiz_list" not in st.session_state: st.session_state.e_quiz_list = []
        if "e_user_answers" not in st.session_state: st.session_state.e_user_answers = {}

        if not st.session_state.exam_started:
            st.info("全データからランダムで **50問** 出題されます。制限時間は **60分** です。")
            if st.button("🔥 模試を開始する（タイマースタート）", type="primary", use_container_width=True):
                target_df = current_data.copy()
                target_df["_original_index"] = target_df.index
                shuffled = target_df.sample(n=min(50, len(target_df))).reset_index(drop=True)
                st.session_state.e_quiz_list = shuffled.to_dict("records")
                st.session_state.e_curr_idx = 0
                st.session_state.e_user_answers = {}
                st.session_state.exam_start_time = time.time()
                st.session_state.exam_started = True
                st.rerun()
        else:
            elapsed_time = int(time.time() - st.session_state.exam_start_time)
            remaining_time = max(0, (60 * 60) - elapsed_time)
            mins, secs = divmod(remaining_time, 60)

            col_t1, col_t2 = st.columns([2, 1])
            with col_t1: st.progress((st.session_state.e_curr_idx) / len(st.session_state.e_quiz_list))
            with col_t2: st.error(f"⏱️ 残り時間: **{mins:02d}分 {secs:02d}秒**")

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
                    orig_idx = q_item.get("_original_index")
                    if is_c:
                        score += 1
                        if orig_idx is not None: st.session_state["wrong_q_indices"].discard(orig_idx)
                    else:
                        if orig_idx is not None: st.session_state["wrong_q_indices"].add(orig_idx)
                        
                    summary_data.append({"問": idx + 1, "問題文": q_txt, "あなたの解答": "、".join(u_ans_list), "正解": "、".join(correct_list), "判定": "⭕ 正解" if is_c else "❌ 不正解"})

                st.markdown(f"### 最終得点: **{score}** / {total_q} 問 (正答率: {int(score/total_q*100)}%)")
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
                if st.button("🔄 もう一度模試を受ける", type="primary"):
                    st.session_state.exam_started = False
                    st.rerun()
            else:
                q = st.session_state.e_quiz_list[curr_idx]
                st.markdown(f"### 第 {curr_idx + 1} 問 / 全 {total_q} 問")
                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")
                display_question_image(q, show_caption=False)

                with st.form(f"exam_form_{curr_idx}"):
                    curr_input = st.text_input("解答を入力", key=f"e_ans_{curr_idx}")
                    sub_next = st.form_submit_button("回答して次の問題へ ➡", use_container_width=True)

                if sub_next:
                    st.session_state.e_user_answers[curr_idx] = [curr_input]
                    st.session_state.e_curr_idx += 1
                    st.rerun()

# --- 6. 苦手克服 ---
elif selected == "苦手克服":
    st.title("🔥 苦手克服モード")
    st.caption("練習モードや本番模試で間違えた問題だけをまとめて集中復習！")
    st.write("---")

    wrong_indices = list(st.session_state.get("wrong_q_indices", set()))
    
    if not wrong_indices:
        st.success("🎉 現在、登録されている苦手問題はありません！順調です！")
    else:
        st.warning(f"現在 **{len(wrong_indices)} 問** の苦手問題が登録されています。")
        
        if "review_started" not in st.session_state: st.session_state.review_started = False
        if "r_curr_idx" not in st.session_state: st.session_state.r_curr_idx = 0
        if "r_quiz_list" not in st.session_state: st.session_state.r_quiz_list = []

        if not st.session_state.review_started:
            if st.button("🔥 苦手問題の復習を開始する", type="primary", use_container_width=True):
                wrong_df = current_data.iloc[wrong_indices].copy()
                wrong_df["_original_index"] = wrong_df.index
                st.session_state.r_quiz_list = wrong_df.to_dict("records")
                st.session_state.r_curr_idx = 0
                st.session_state.review_started = True
                st.rerun()
        else:
            total_q = len(st.session_state.r_quiz_list)
            curr_idx = st.session_state.r_curr_idx

            if curr_idx >= total_q:
                st.balloons()
                st.markdown("## 🎉 苦手克服トレーニング完了！")
                if st.button("🔄 ホームへ戻る", type="primary"):
                    st.session_state.review_started = False
                    st.rerun()
            else:
                q = st.session_state.r_quiz_list[curr_idx]
                st.progress((curr_idx) / total_q)
                st.markdown(f"### 苦手復習 第 {curr_idx + 1} 問 / 全 {total_q} 問")

                question_text, correct_ans_raw = format_question_and_answer(q)
                st.info(f"**【問題】**\n{question_text}")
                display_question_image(q, show_caption=False)

                correct_list = get_correct_answers_list(q, correct_ans_raw)

                with st.form(f"review_form_{curr_idx}"):
                    u_input = st.text_input("解答を入力", key=f"r_ans_{curr_idx}")
                    sub_rev = st.form_submit_button("回答する", use_container_width=True)

                if sub_rev:
                    is_correct = check_answers_multi([u_input], correct_list)
                    disp_ans = "、".join(correct_list)
                    orig_idx = q.get("_original_index")
                    if is_correct:
                        st.success("⭕ 克服成功！苦手リストから削除しました。")
                        if orig_idx is not None: st.session_state["wrong_q_indices"].discard(orig_idx)
                    else:
                        st.error(f"❌ 残念... 正解は: **{disp_ans}**")

                    exp = get_clean_str(q.get("explanation") or q.get("解説"))
                    if exp: st.caption(f"💡 【解説】: {exp}")
                    st.session_state.r_curr_idx += 1
                    st.button("次へ ➡")

# --- 7. AI検索モード ---
elif selected == "AI検索モード":
    st.title("🔍 AI検索モード")
    st.caption("〜 キャラクターマスタ＆問題データベース 爆速逆引き図鑑 〜")
    st.write("---")

    if current_data.empty:
        st.error("データが見つかりません。")
    else:
        search_query = st.text_input("🔍 キーワード検索", "", placeholder="名前・悪魔の実・技・所属・問題文・解説など")
        filtered_df = current_data.copy()
        if search_query:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
            filtered_df = filtered_df[mask]

        st.markdown(f"検索結果: **{len(filtered_df)}** 件")
        st.dataframe(filtered_df, use_container_width=True)

# --- 8. データ追加・編集 ---
elif selected == "データ追加・編集":
    st.title("➕ データ追加・編集")
    tab_titles = ["📝 1. データの新規追加", "✏️ 2. データの編集・削除"]

    if "edit_active_tab" in st.session_state:
        req_tab = st.session_state.pop("edit_active_tab")
        if isinstance(req_tab, int) and 0 <= req_tab < len(tab_titles):
            st.session_state["data_edit_tab_radio"] = tab_titles[req_tab]

    if "target_edit_global_index" in st.session_state or "edit_target_index" in st.session_state:
        st.session_state["data_edit_tab_radio"] = tab_titles[1]

    if "data_edit_tab_radio" not in st.session_state or st.session_state["data_edit_tab_radio"] not in tab_titles:
        st.session_state["data_edit_tab_radio"] = tab_titles[0]

    tab_selection = st.radio("操作を選択してください", tab_titles, key="data_edit_tab_radio", horizontal=True)

    if tab_selection == "📝 1. データの新規追加":
        st.subheader("📝 新しい問題データの追加")
        type_options = ["一問一答", "一問多答", "順序選択", "6文字並べ替え", "組み合わせ", "自由記述"]
        selected_type = st.selectbox("問題形式を選んでください", options=type_options, key="add_type_select")

        with st.form(key="add_new_question_detail_form"):
            new_question = st.text_area("【問題文】*", placeholder="問題文を入力してください", height=100)
            new_story = st.text_input("【ストーリー（編・章）】", placeholder="例: アラバスタ編")
            q_img_file = st.file_uploader("🖼️ 問題用画像（任意）", type=["png", "jpg", "jpeg", "webp"])
            
            new_answer = st.text_input("解答・正解*")
            new_explanation = st.text_area("【解説】")
            submit_btn = st.form_submit_button("➕ 新規問題を保存して追加", use_container_width=True)

            if submit_btn:
                if not new_question.strip():
                    st.error("問題文を入力してください。")
                else:
                    final_q_img = ""
                    if q_img_file is not None:
                        bytes_data = q_img_file.getvalue()
                        base64_str = base64.b64encode(bytes_data).decode("utf-8")
                        final_q_img = f"data:{q_img_file.type};base64,{base64_str}"

                    new_entry = {
                        "type": selected_type,
                        "question": new_question,
                        "answer": new_answer,
                        "explanation": new_explanation,
                        "image": final_q_img,
                        "story": new_story
                    }

                    st.session_state["working_df"] = pd.concat([st.session_state["working_df"], pd.DataFrame([new_entry])], ignore_index=True)
                    st.success("新しい問題データを追加しました！")
                    st.rerun()

    elif tab_selection == "✏️ 2. データの編集・削除":
        st.subheader("🛠️ 問題修正・削除フォーム")
        
        target_idx = None
        if "target_edit_global_index" in st.session_state:
            target_idx = st.session_state.pop("target_edit_global_index")
        elif "edit_target_index" in st.session_state:
            target_idx = st.session_state.pop("edit_target_index")

        forced_pos = None
        if target_idx is not None:
            try:
                t_val = int(target_idx)
                if 0 <= t_val < len(current_data): forced_pos = t_val
            except Exception: pass

        def make_label(i):
            row = current_data.iloc[i]
            q_text = get_clean_str(row.get("question") or row.get("name") or row.get("問題") or "")
            return f"【No.{i+1}】 {q_text[:35]}..."

        selected_pos = st.selectbox("編集する問題を選択", options=list(range(len(current_data))), index=forced_pos if forced_pos is not None else 0, format_func=make_label)

        if len(current_data) > 0:
            selected_row = current_data.iloc[selected_pos]
            with st.form(key=f"edit_form_{selected_pos}"):
                edited_data = {}
                for col in current_data.columns:
                    val = selected_row.get(col, "")
                    val_str = "" if pd.isna(val) else str(val)
                    edited_data[col] = st.text_input(f"【{col}】", value=val_str)

                if st.form_submit_button("💾 変更を保存する", use_container_width=True):
                    for col, new_val in edited_data.items():
                        st.session_state["working_df"].at[selected_pos, col] = new_val
                    st.success(f"No.{selected_pos + 1} の更新を保存しました！")
                    st.rerun()

            with st.expander("🗑️ この問題を削除する"):
                if st.button("🚨 問題を完全に削除", type="primary", key=f"btn_del_{selected_pos}"):
                    st.session_state["working_df"] = st.session_state["working_df"].drop(index=selected_pos).reset_index(drop=True)
                    st.success("データを削除しました。")
                    st.rerun()

# --- 9. キャラクターデータモード ---
elif selected == "キャラクターデータ":
    st.title("🏴 キャラクター名鑑")
    st.caption("登録されているキャラクターの一覧・詳細情報を閲覧できます。")
    st.markdown("---")

    if current_data.empty:
        st.info("登録されているデータがありません。")
    else:
        search_kw = st.text_input("🔍 キャラクター検索", placeholder="名前・異名・所属など")
        char_df = current_data.copy()
        char_df["_orig_row_id"] = char_df.index

        if search_kw:
            mask = char_df.astype(str).apply(lambda x: x.str.contains(search_kw, case=False, na=False)).any(axis=1)
            char_df = char_df[mask]

        st.write(f"表示中のデータ件数: **{len(char_df)}** 件")
        st.markdown("---")

        cols = st.columns(3)
        for idx, (_, row) in enumerate(char_df.iterrows()):
            orig_row_id = int(row["_orig_row_id"])
            c_name = get_clean_str(row.get("name") or row.get("名前") or row.get("question") or f"データ No.{orig_row_id + 1}")
            c_nick = get_clean_str(row.get("nickname") or row.get("異名"))
            c_img = get_clean_str(row.get("image") or row.get("画像"))
            c_aff = get_clean_str(row.get("affiliation") or row.get("所属"))
            c_fruit = get_clean_str(row.get("devil_fruit") or row.get("悪魔の実") or row.get("answer"))
            c_desc = get_clean_str(row.get("explanation") or row.get("解説"))

            with cols[idx % 3]:
                with st.container(border=True):
                    if c_img:
                        st.image(c_img, use_container_width=True)
                    else:
                        st.caption("🖼️ 画像なし")

                    st.markdown(f"### {c_name}")
                    if c_nick: st.caption(f"【異名】{c_nick}")
                    st.markdown("---")
                    if c_aff: st.write(f"**🏴 所属:** {c_aff}")
                    if c_fruit: st.write(f"**🍈 能力/解答:** {c_fruit}")
                    if c_desc:
                        with st.expander("📝 詳細・解説"): st.write(c_desc)

                    if st.button("✏️ このデータを編集", key=f"btn_edit_char_{orig_row_id}", use_container_width=True):
                        st.session_state["target_edit_global_index"] = orig_row_id
                        st.session_state["edit_active_tab"] = 1
                        st.session_state["data_edit_tab_radio"] = "✏️ 2. データの編集・削除"
                        st.session_state["current_nav"] = "データ追加・編集"
                        st.rerun()
