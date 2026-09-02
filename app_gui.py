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

# --- データフレームの完全浄化 ---
def deep_clean_dataframe(df):
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(lambda x: x.iloc[0] if isinstance(x, (pd.DataFrame, pd.Series)) else x)
        df[col] = df[col].map(lambda x: "" if pd.isna(x) or str(x).lower() in ["nan", "none", "<na>"] else str(x))
    return df

# --- 1. データ読み込み＆セッション状態管理 ---
@st.cache_data
def load_all_data():
    files = glob.glob("*.xlsx")
    if not files:
        return pd.DataFrame(), pd.DataFrame()

    df_list = []
    char_df = pd.DataFrame()

    for f in files:
        try:
            if "character_master" in f:
                xls = pd.ExcelFile(f)
                char_df = pd.read_excel(f, sheet_name=xls.sheet_names[0])
            else:
                temp_df = pd.read_excel(f)
                temp_df["source_file"] = f
                df_list.append(temp_df)
        except Exception:
            continue

    df_all = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    return deep_clean_dataframe(df_all), deep_clean_dataframe(char_df)

df_all, character_master_df = load_all_data()

required_char_cols = [
    "characterid", "name", "image", "bounty", "birthday", 
    "age", "birth_place", "affiliation", "weapon", "nickname", 
    "devil_fruit", "fruit_type"
]
for col in required_char_cols:
    if col not in character_master_df.columns:
        character_master_df[col] = ""

if "working_df" not in st.session_state or st.session_state["working_df"] is None or st.session_state["working_df"].empty:
    st.session_state["working_df"] = df_all.copy().reset_index(drop=True)

if "char_working_df" not in st.session_state or st.session_state["char_working_df"] is None or st.session_state["char_working_df"].empty:
    st.session_state["char_working_df"] = character_master_df.copy().reset_index(drop=True)

st.session_state["working_df"] = deep_clean_dataframe(st.session_state["working_df"])
st.session_state["char_working_df"] = deep_clean_dataframe(st.session_state["char_working_df"])

if "wrong_q_indices" not in st.session_state:
    st.session_state["wrong_q_indices"] = set()

if "quiz_stats" not in st.session_state:
    st.session_state["quiz_stats"] = {}

if "practice_active" not in st.session_state:
    st.session_state["practice_active"] = False

if "inline_edit_index" not in st.session_state:
    st.session_state["inline_edit_index"] = None

if "last_judge_result" not in st.session_state:
    st.session_state["last_judge_result"] = None

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
    if row is None:
        return
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
    if q is None:
        return []
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
    if q is None:
        return "このキャラクターの名前は？", ""
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
    
    current_selection = st.session_state["current_nav"]
    def_idx = menu_options.index(current_selection) if current_selection in menu_options else 0

    selected = option_menu(
        menu_title=None,
        options=menu_options,
        icons=["house", "book", "trophy", "fire", "search", "pencil", "person"],
        default_index=def_idx,
        key="main_menu_nav"
    )
    
    st.session_state["current_nav"] = selected
    
    st.divider()
    st.markdown("### 📊 学習ステータス")
    current_total_q = len(st.session_state.get("working_df", pd.DataFrame()))
    current_wrong_q = len(st.session_state.get("wrong_q_indices", set()))
    st.metric(label="📚 登録総問題数", value=f"{current_total_q:,} 問")
    st.metric(label="🔥 苦手問題数", value=f"{current_wrong_q:,} 問")

current_data = st.session_state.get("working_df", pd.DataFrame())
char_data = st.session_state.get("char_working_df", pd.DataFrame())

# --- 各画面のレンダリング ---
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
        sample_imgs = random.sample(all_imgs, min(len(all_imgs), 20))
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
        .wt-hero-container {{ position: relative; width: 100%; height: 500px; background-color: #000; overflow: hidden; border-radius: 12px; }}
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
        components.html(wt100_full_html, height=520)
    else:
        st.warning("表示できる画像ファイルが見つかりません。")

    st.write("")
    st.subheader("⚡ クイックアクセス")
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        if st.button("📖 練習モードを始める", use_container_width=True, type="primary"):
            st.session_state["current_nav"] = "練習モード"
            st.rerun()
    with q_col2:
        if st.button("🏆 本番模試に挑戦する", use_container_width=True):
            st.session_state["current_nav"] = "本番模試"
            st.rerun()
    with q_col3:
        if st.button("🔥 苦手克服モードへ", use_container_width=True):
            st.session_state["current_nav"] = "苦手克服"
            st.rerun()

elif selected == "練習モード":
    st.title("📖 練習モード ＆ 苦手克服")
    
    df = st.session_state.get("working_df", pd.DataFrame())
    if df.empty:
        st.warning("問題データが読み込まれていません。「データ編集」タブからデータを準備してください。")
    else:
        if not st.session_state["practice_active"]:
            stats = st.session_state.get("quiz_stats", {})
            wrong_set = st.session_state.get("wrong_q_indices", set())
            
            mastered_count = 0
            learning_count = 0
            weak_count = 0
            untested_count = 0
            
            for idx in range(len(df)):
                if idx in wrong_set:
                    weak_count += 1
                elif idx in stats:
                    st_data = stats[idx]
                    total = st_data.get("total", 0)
                    correct = st_data.get("correct", 0)
                    if total > 0:
                        rate = correct / total
                        if rate >= 0.8:
                            mastered_count += 1
                        else:
                            learning_count += 1
                    else:
                        untested_count += 1
                else:
                    untested_count += 1

            col_g1, col_g2 = st.columns([1, 2])
            with col_g1:
                st.markdown("### 📊 習熟度バランス")
                summary_df = pd.DataFrame({
                    "状態": ["得意 (正答率80%~)", "学習中", "苦手・不正解", "未挑戦"],
                    "問題数": [mastered_count, learning_count, weak_count, untested_count]
                })
                st.dataframe(summary_df, hide_index=True, use_container_width=True)
                
            with col_g2:
                import altair as alt
                chart_data = summary_df[summary_df["問題数"] > 0]
                if not chart_data.empty:
                    pie_chart = alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta(field="問題数", type="quantitative"),
                        color=alt.Color(field="状態", type="nominal", scale=alt.Scale(scheme="category10")),
                        tooltip=["状態", "問題数"]
                    ).properties(height=220)
                    st.altair_chart(pie_chart, use_container_width=True)
                else:
                    st.info("まだ回答データがありません。問題を解くと円グラフに反映されます。")

            st.divider()

            st.subheader("⚙️ 出題設定")
            mode_tab = st.radio(
                "出題モードを選択",
                ["ランダム出題", "🔥 苦手・不正解集中特訓", "🎯 スマート自動振り分け（弱点優先）"],
                horizontal=True
            )
            
            st.write("")
            if st.button("🚀 練習をスタートする", type="primary", use_container_width=True):
                if mode_tab == "ランダム出題":
                    targets = list(range(len(df)))
                elif mode_tab == "🔥 苦手・不正解集中特訓":
                    targets = list(wrong_set)
                else:
                    targets = [i for i in range(len(df)) if i in wrong_set or i not in stats or (stats[i].get("correct", 0)/max(1, stats[i].get("total", 1)) < 0.6)]
                    if not targets:
                        targets = list(range(len(df)))
                
                if mode_tab == "🔥 苦手・不正解集中特訓" and not targets:
                    st.error("現在、苦手・不正解に登録されている問題はありません！")
                else:
                    st.session_state["practice_targets"] = targets
                    st.session_state["practice_mode_sel"] = mode_tab
                    st.session_state["practice_current_idx"] = random.choice(targets)
                    st.session_state["practice_answered"] = False
                    st.session_state["inline_edit_index"] = None
                    st.session_state["last_judge_result"] = None
                    st.session_state["practice_active"] = True
                    st.rerun()

        else:
            target_indices = st.session_state.get("practice_targets", list(range(len(df))))
            mode_name = st.session_state.get("practice_mode_sel", "ランダム出題")

            col_top1, col_top2 = st.columns([4, 1])
            with col_top1:
                st.markdown(f"**現在のモード:** `{mode_name}` （対象問題数: {len(target_indices)}問）")
            with col_top2:
                if st.button("⬅️ モード選択に戻る"):
                    st.session_state["practice_active"] = False
                    st.session_state["inline_edit_index"] = None
                    st.session_state["last_judge_result"] = None
                    st.rerun()

            st.divider()

            if not target_indices:
                st.warning("出題できる問題がありません。")
                if st.button("モード選択に戻る"):
                    st.session_state["practice_active"] = False
                    st.session_state["inline_edit_index"] = None
                    st.session_state["last_judge_result"] = None
                    st.rerun()
            else:
                current_idx = st.session_state.get("practice_current_idx", target_indices[0])
                if current_idx not in target_indices:
                    current_idx = random.choice(target_indices)
                    st.session_state["practice_current_idx"] = current_idx

                row = df.iloc[current_idx]
                q_text, correct_ans = format_question_and_answer(row)
                correct_answers_list = get_correct_answers_list(row, correct_ans)

                st.markdown(f"**【問題 ID / インデックス: {current_idx}】**")
                
                col_q_title, col_edit_btn = st.columns([5, 1])
                with col_q_title:
                    st.subheader(q_text)
                with col_edit_btn:
                    if st.button("✏️ この問題を修正", key=f"edit_jump_{current_idx}"):
                        if st.session_state.get("inline_edit_index") == current_idx:
                            st.session_state["inline_edit_index"] = None
                        else:
                            st.session_state["inline_edit_index"] = current_idx
                        st.rerun()

                display_question_image(row, width=250)

                answered_state = st.session_state.get("practice_answered", False)

                # --- 判定結果の表示（rerunの前にセッションに保持して確実に描画） ---
                if answered_state and st.session_state.get("last_judge_result"):
                    res = st.session_state["last_judge_result"]
                    if res["is_correct"]:
                        st.success("🎉 正解です！お見事！")
                    else:
                        st.error(f"❌ 残念！不正解です。正解は: 『 {' / '.join(correct_answers_list)} 』 です。")

                with st.form(key=f"quiz_form_{current_idx}"):
                    if not answered_state:
                        user_input = st.text_input("解答を入力してください（Enterキーで解答）:", key=f"practice_input_{current_idx}")
                        submitted = st.form_submit_button("解答する", type="primary")
                        
                        if submitted:
                            st.session_state["practice_answered"] = True
                            if current_idx not in st.session_state["quiz_stats"]:
                                st.session_state["quiz_stats"][current_idx] = {"total": 0, "correct": 0}
                            st.session_state["quiz_stats"][current_idx]["total"] += 1

                            is_correct = False
                            if user_input:
                                is_correct = check_answers_multi([user_input], correct_answers_list)
                            
                            if is_correct:
                                st.session_state["quiz_stats"][current_idx]["correct"] += 1
                                if current_idx in st.session_state["wrong_q_indices"]:
                                    st.session_state["wrong_q_indices"].remove(current_idx)
                            else:
                                st.session_state["wrong_q_indices"].add(current_idx)

                            st.session_state["last_judge_result"] = {"is_correct": is_correct}
                            st.rerun()
                    else:
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            next_btn = st.form_submit_button("次の問題へ ➡️", type="primary", use_container_width=True)
                        with col_btn2:
                            stop_btn = st.form_submit_button("⏹️ 中断する", use_container_width=True)

                        if next_btn:
                            st.session_state["practice_current_idx"] = random.choice(target_indices)
                            st.session_state["practice_answered"] = False
                            st.session_state["inline_edit_index"] = None
                            st.session_state["last_judge_result"] = None
                            st.rerun()
                        elif stop_btn:
                            st.session_state["practice_active"] = False
                            st.session_state["inline_edit_index"] = None
                            st.session_state["last_judge_result"] = None
                            st.rerun()

                if st.session_state.get("inline_edit_index") == current_idx:
                    st.markdown("---")
                    st.markdown(f"#### 🛠️ インデックス [{current_idx}] のインライン編集＆保存")
                    with st.form(key=f"inline_edit_form_{current_idx}"):
                        updated_values = {}
                        for col in df.columns:
                            if col == "source_file":
                                continue
                            val = str(row[col]) if pd.notna(row[col]) else ""
                            updated_values[col] = st.text_input(f"列: {col}", value=val, key=f"inline_{current_idx}_{col}")

                        col_save, col_cancel = st.columns([1, 1])
                        with col_save:
                            save_btn = st.form_submit_button("💾 変更を保存して次の問題へ", type="primary", use_container_width=True)
                        with col_cancel:
                            cancel_btn = st.form_submit_button("キャンセル", use_container_width=True)

                        if save_btn:
                            for col, val in updated_values.items():
                                st.session_state["working_df"].at[current_idx, col] = val
                            st.success(f"インデックス [{current_idx}] のデータを更新しました！")
                            st.session_state["inline_edit_index"] = None
                            st.session_state["practice_answered"] = False
                            st.session_state["last_judge_result"] = None
                            st.session_state["practice_current_idx"] = random.choice(target_indices)
                            time.sleep(0.5)
                            st.rerun()
                        elif cancel_btn:
                            st.session_state["inline_edit_index"] = None
                            st.rerun()

elif selected == "本番模試":
    pass

elif selected == "苦手克服":
    st.title("🔥 苦手克服モード")
    st.info("「練習モード」の中に苦手克服機能が統合されました。左側のメニューから「練習モード」を選択し、「🔥 苦手・不正解集中特訓」をご利用ください。")
    if st.button("練習モードへ移動する", type="primary"):
        st.session_state["current_nav"] = "練習モード"
        st.rerun()

elif selected == "AI検索":
    pass

elif selected == "データ編集":
    st.title("✏️ データ編集・修正モード")
    df = st.session_state.get("working_df", pd.DataFrame())
    
    if df.empty:
        st.warning("編集するデータがありません。")
    else:
        selected_row_idx = st.number_input(
            "編集する行インデックスを指定",
            min_value=0,
            max_value=len(df) - 1,
            value=0,
            step=1
        )
        
        st.markdown(f"--- \n### 📝 インデックス [{selected_row_idx}] の編集")
        row_data = df.iloc[selected_row_idx]

        with st.form(key="edit_form"):
            updated_values = {}
            for col in df.columns:
                if col == "source_file":
                    continue
                val = str(row_data[col]) if pd.notna(row_data[col]) else ""
                updated_values[col] = st.text_input(f"列: {col}", value=val)

            save_btn = st.form_submit_button("💾 変更を保存する", type="primary")
            if save_btn:
                for col, val in updated_values.items():
                    st.session_state["working_df"].at[selected_row_idx, col] = val
                st.success(f"インデックス [{selected_row_idx}] のデータを更新しました！")
                time.sleep(0.8)
                st.rerun()

elif selected == "キャラ名鑑":
    pass
