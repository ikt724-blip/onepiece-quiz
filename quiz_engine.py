import streamlit as st
import pandas as pd
import random
import os
from quiz_ui import display_quiz_ui

def norm(txt): return st.session_state.normalize_func(txt)

def render_quiz_page():
    df_master = st.session_state.df_master
    df_mondai = st.session_state.df_mondai

    if (df_master is None or df_master.empty) and (df_mondai is None or df_mondai.empty):
        st.warning("出題できるデータ（character_master.xlsx または 問題集.xlsx）が空っぽです。")
        return

    # コース選択
    if 'quiz_pool' not in st.session_state:
        st.markdown("### 📋 挑戦するコースを選択してください")
        col1, col2 = st.columns(2)
        course_size = 0
        if col1.button("🔥 ランダム 50問コース", use_container_width=True): course_size = 50
        if col2.button("👑 ランダム 100問コース", use_container_width=True): course_size = 100
        
        if course_size > 0:
            pool_custom, pool_bday, pool_text, pool_choice, pool_image, pool_nick = [], [], [], [], [], []
            
            # 問題集.xlsx
            if df_mondai is not None and not df_mondai.empty:
                for _, row in df_mondai.iterrows():
                    q_txt = str(row.get('question', '')).strip()
                    a_txt = str(row.get('answer', '')).strip()
                    q_type = str(row.get('type', 'text')).strip()
                    if q_txt and a_txt and q_txt != "nan" and a_txt != "nan":
                        if q_type == 'text_multi' or ',' in a_txt or '、' in a_txt:
                            answers = [ans.strip() for ans in a_txt.replace('、', ',').split(',') if ans.strip()]
                            pool_custom.append({"type": "text_multi", "question": q_txt, "correct": answers, "source": "問題集.xlsx"})
                        else:
                            pool_custom.append({"type": q_type, "question": q_txt, "correct": a_txt, "source": "問題集.xlsx"})
            
            # character_master.xlsx
            if df_master is not None and not df_master.empty:
                all_names = [str(n).strip() for n in df_master['name'].dropna().unique() if str(n).strip() not in ["", "nan"]]
                all_bdays = [str(b).strip() for b in df_master['birthday'].dropna().unique() if str(b).strip() not in ["", "nan"]]

                for _, row in df_master.iterrows():
                    name = str(row.get('name', '')).strip()
                    fruit = str(row.get('devil_fruit', '')).strip()
                    f_type = str(row.get('fruit_type', '')).strip()
                    birthday = str(row.get('birthday', '')).strip()
                    img_file = str(row.get('image', '')).strip()
                    nickname_raw = str(row.get('nickname', '')).strip()
                    
                    if pd.notna(row.get('name')) and name != "nan" and name != "":
                        full_img_path = os.path.join("images", img_file)
                        if pd.notna(row.get('image')) and img_file != "nan" and img_file != "" and os.path.exists(full_img_path):
                            other_names = [n for n in all_names if n != name]
                            if len(other_names) >= 3:
                                dummy_names = random.sample(other_names, 3)
                                img_choices = dummy_names + [name]
                                random.shuffle(img_choices)
                                pool_image.append({"type": "image_choice", "question": "この画像（コマ）の人物は誰？", "correct": name, "pool": img_choices, "image_path": full_img_path, "source": "character_master.xlsx", "target_name": name})
                            pool_image.append({"type": "image_text", "question": "この画像（コマ）の人物の名前は誰？", "correct": name, "image_path": full_img_path, "source": "character_master.xlsx", "target_name": name})
                        
                        if pd.notna(row.get('devil_fruit')) and fruit != "nan" and fruit != "":
                            pool_text.append({"type": "text", "question": f"【 {fruit} 】 の能力者は誰？", "correct": name, "source": "character_master.xlsx", "target_name": name})
                            if pd.notna(row.get('fruit_type')) and f_type != "nan" and f_type != "":
                                pool_choice.append({"type": "choice", "question": f"【 {fruit} 】 は何系（系統）の悪魔の実？", "correct": f_type, "pool": ["超人系", "動物系", "自然系", "動物系(幻獣種)", "動物系(古代種)"], "source": "character_master.xlsx", "target_name": name})
                        
                        if pd.notna(row.get('birthday')) and birthday != "nan" and birthday != "":
                            other_bdays = [b for b in all_bdays if b != birthday]
                            if len(other_bdays) >= 3:
                                dummy_bdays = random.sample(other_bdays, 3)
                                bday_choices = dummy_bdays + [birthday]
                                random.shuffle(bday_choices)
                                pool_bday.append({"type": "choice", "question": f"【 {name} 】 の誕生日はどれ？", "correct": birthday, "pool": bday_choices, "source": "character_master.xlsx", "target_name": name})

                        if pd.notna(row.get('nickname')) and nickname_raw != "nan" and nickname_raw != "":
                            nicknames = [n.strip() for n in nickname_raw.split(',') if n.strip()]
                            for nick in nicknames:
                                pool_nick.append({"type": "text", "question": f"【 {nick} 】 と呼ばれる人物の本名は？", "correct": name, "source": "character_master.xlsx", "target_name": name})
            
            for p in [pool_custom, pool_bday, pool_text, pool_choice, pool_image, pool_nick]: random.shuffle(p)
            
            all_rooms = [pool_custom, pool_bday, pool_text, pool_choice, pool_image, pool_nick]
            active_rooms = [r for r in all_rooms if len(r) > 0]
            room_count = len(active_rooms) if len(active_rooms) > 0 else 1
            target_per_room = course_size // room_count
            
            selected_pool = []
            for room in active_rooms: selected_pool += room[:target_per_room]
            
            remains = []
            for room in active_rooms: remains += room[target_per_room:]
            random.shuffle(remains)
            needed = course_size - len(selected_pool)
            if needed > 0 and len(remains) >= needed: selected_pool += remains[:needed]
            
            random.shuffle(selected_pool)
            actual_size = min(course_size, len(selected_pool))
            
            if actual_size == 0: st.error("❌ クイズデータが見つかりません。")
            else:
                st.session_state.quiz_pool = selected_pool[:actual_size]
                st.session_state.c_index = 0; st.session_state.c_score = 0; st.session_state.is_answered = False; st.session_state.u_text = ""; st.session_state.sel_choice = None; st.session_state.is_force_quit = False
                st.rerun()
                
    # 試験リザルト画面
    elif st.session_state.c_index >= len(st.session_state.quiz_pool) or st.session_state.is_force_quit:
        st.balloons()
        if st.session_state.is_force_quit: st.warning("🏳️ テストを途中で中断しました。")
        else: st.success("👑 全問試験終了！お疲れ様でした！")
        total = max(1, st.session_state.c_index)
        st.metric("集計スコア", f"{st.session_state.c_score} / {total} 問", f"正解率 {(st.session_state.c_score / total) * 100:.1f}%")
        if st.button("🔄 コース選択に戻る", use_container_width=True): 
            del st.session_state.quiz_pool
            st.rerun()
            
    # メイン進行ループ
    else:
        q = st.session_state.quiz_pool[st.session_state.c_index]
        idx = st.session_state.c_index
        total = len(st.session_state.quiz_pool)
        
        # ナレッジキング風 カード
        st.markdown(f"""
            <div style="background-color: #ffffff; border: 2px solid #222222; border-radius: 16px; padding: 24px 20px 20px 20px; position: relative; margin-top: 20px; margin-bottom: 20px; text-align: center;">
                <div style="position: absolute; top: -16px; left: 50%; transform: translateX(-50%); background-color: #ffffff; border: 2px solid #222222; border-radius: 20px; padding: 2px 20px; font-weight: 900; font-size: 16px; color: #111111;">
                    第 {idx + 1} 問 <span style="font-size:12px; font-weight:normal; color:#666;">/{total}</span>
                </div>
                <div style="font-size: 16px; font-weight: 800; color: #111111; margin-top: 10px; line-height: 1.5;">
                    {q['question']}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if 'image_path' in q and os.path.exists(q['image_path']):
            st.image(q['image_path'], use_container_width=True)
            
        user_answered = st.session_state.is_answered
        
        # UI描画
        display_quiz_ui(q['type'], idx, q, user_answered)

        st.write("")
        
        if not st.session_state.is_answered:
            # 未解答状態
            st.markdown('<div class="submit-container">', unsafe_allow_html=True)
            with st.form(key=f"submit_form_{idx}"):
                sub_btn = st.form_submit_button("決定", use_container_width=True)
                if sub_btn:
                    st.session_state.is_answered = True
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            c_pass, c_quit = st.columns(2)
            with c_pass:
                st.markdown('<div class="pass-btn">', unsafe_allow_html=True)
                if st.button("パスする（後回し）", key=f"pass_btn_{idx}", use_container_width=True):
                    prob = st.session_state.quiz_pool.pop(st.session_state.c_index)
                    st.session_state.quiz_pool.append(prob)
                    st.toast("📌 後回しにしました！")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c_quit:
                st.markdown('<div class="quit-btn">', unsafe_allow_html=True)
                if st.button("中断する", key=f"quit_btn_{idx}", use_container_width=True):
                    st.session_state.is_force_quit = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            # 正誤判定
            is_current_correct = False
            if q['type'] == 'text_multi':
                user_inputs = [norm(x) for x in st.session_state.u_text if norm(x) != ""]
                correct_inputs = [norm(x) for x in q['correct']]
                is_current_correct = (sorted(user_inputs) == sorted(correct_inputs))
            elif q['type'] in ['text', 'fill_blank', 'image_text']:
                alts = [norm(a) for a in q.get('alternatives', [])]
                is_current_correct = (norm(st.session_state.u_text) == norm(q['correct'])) or (norm(st.session_state.u_text) in alts)
            else:
                is_current_correct = (norm(st.session_state.sel_choice) == norm(q['correct']))

            # 結果表示
            if is_current_correct:
                st.session_state.c_score += 1
                st.success("⭕ 正解！！ さすがナレッジキング候補！")
            else:
                ans_disp = " / ".join(q['correct']) if isinstance(q['correct'], list) else q['correct']
                st.error(f"❌ 不正解... 正解は 【 {ans_disp} 】 です。")
            
            # フォーカス
            st.components.v1.html(
                """
                <script>
                    window.parentElement.document.querySelector('button[kind="primary"]').focus();
                </script>
                """,
                height=0
            )

            # 「次の問題へ進む」ボタン
            with st.form(key=f"next_form_{idx}"):
                next_submit = st.form_submit_button("➡️ 次の問題へ進む (Enterキー)", use_container_width=True)
            if next_submit:
                st.session_state.c_index += 1
                st.session_state.is_answered = False
                st.session_state.sel_choice = None
                st.session_state.u_text = ""
                st.rerun()

            st.write("---")
            # 🛠️ 直ちにExcel修正ページへジャンプするボタン
            if st.button("🛠️ この問題をデータ修正（Excel更新）する", key=f"edit_jump_{idx}", use_container_width=True):
                st.session_state.edit_target_q = q
                st.session_state.nav_index = 4  # 「データ追加」タブのインデックス
                st.rerun()