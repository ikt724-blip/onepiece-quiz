import streamlit as st
import pandas as pd
import random
import os

def norm(txt): return st.session_state.normalize_func(txt)

def render_quiz_page():
    df_master = st.session_state.df_master
    df_mondai = st.session_state.df_mondai

    if (df_master is None or df_master.empty) and (df_mondai is None or df_mondai.empty):
        st.warning("出題できるデータが空っぽです。")
        return

    # コース選択画面
    if 'quiz_pool' not in st.session_state:
        st.markdown("### 📋 挑戦するコースを選択してください")
        col1, col2 = st.columns(2)
        course_size = 0
        if col1.button("🔥 ランダム 50問コース", use_container_width=True): course_size = 50
        if col2.button("👑 ランダム 100問コース", use_container_width=True): course_size = 100
        
        if course_size > 0:
            pool_custom, pool_bday, pool_text, pool_choice, pool_image, pool_nick = [], [], [], [], [], []
            
            if df_mondai is not None and not df_mondai.empty:
                for idx_row, row in df_mondai.iterrows():
                    q_txt = str(row.get('question', '')).strip()
                    a_txt = str(row.get('answer', '')).strip()
                    q_type = str(row.get('type', 'text')).strip()
                    if q_txt and a_txt and q_txt != "nan" and a_txt != "nan":
                        if q_type == 'text_multi' or ',' in a_txt or '、' in a_txt:
                            answers = [ans.strip() for ans in a_txt.replace('、', ',').split(',') if ans.strip()]
                            pool_custom.append({"type": "text_multi", "question": q_txt, "correct": answers, "source": "問題集.xlsx", "row_idx": idx_row})
                        else:
                            pool_custom.append({"type": q_type, "question": q_txt, "correct": a_txt, "source": "問題集.xlsx", "row_idx": idx_row})
            
            if df_master is not None and not df_master.empty:
                all_names = [str(n).strip() for n in df_master['name'].dropna().unique() if str(n).strip() not in ["", "nan"]]
                all_bdays = [str(b).strip() for b in df_master['birthday'].dropna().unique() if str(b).strip() not in ["", "nan"]]

                for idx_row, row in df_master.iterrows():
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
                                pool_image.append({"type": "image_choice", "question": "この画像（コマ）の人物は誰？", "correct": name, "pool": img_choices, "image_path": full_img_path, "source": "character_master.xlsx", "target_name": name, "row_idx": idx_row})
                            pool_image.append({"type": "image_text", "question": "この画像（コマ）の人物の名前は誰？", "correct": name, "image_path": full_img_path, "source": "character_master.xlsx", "target_name": name, "row_idx": idx_row})
                        
                        if pd.notna(row.get('devil_fruit')) and fruit != "nan" and fruit != "":
                            pool_text.append({"type": "text", "question": f"【 {fruit} 】 の能力者は誰？", "correct": name, "source": "character_master.xlsx", "target_name": name, "row_idx": idx_row})
                            if pd.notna(row.get('fruit_type')) and f_type != "nan" and f_type != "":
                                pool_choice.append({"type": "choice", "question": f"【 {fruit} 】 は何系（系統）の悪魔の実？", "correct": f_type, "pool": ["超人系", "動物系", "自然系", "動物系(幻獣種)", "動物系(古代種)"], "source": "character_master.xlsx", "target_name": name, "row_idx": idx_row})
                        
                        if pd.notna(row.get('birthday')) and birthday != "nan" and birthday != "":
                            other_bdays = [b for b in all_bdays if b != birthday]
                            if len(other_bdays) >= 3:
                                dummy_bdays = random.sample(other_bdays, 3)
                                bday_choices = dummy_bdays + [birthday]
                                random.shuffle(bday_choices)
                                pool_bday.append({"type": "choice", "question": f"【 {name} 】 の誕生日はどれ？", "correct": birthday, "pool": bday_choices, "source": "character_master.xlsx", "target_name": name, "row_idx": idx_row})

                        if pd.notna(row.get('nickname')) and nickname_raw != "nan" and nickname_raw != "":
                            nicknames = [n.strip() for n in nickname_raw.split(',') if n.strip()]
                            for nick in nicknames:
                                pool_nick.append({"type": "text", "question": f"【 {nick} 】 と呼ばれる人物の本名は？", "correct": name, "source": "character_master.xlsx", "target_name": name, "row_idx": idx_row})
            
            all_rooms = [pool_custom, pool_bday, pool_text, pool_choice, pool_image, pool_nick]
            active_rooms = [r for r in all_rooms if len(r) > 0]
            target_per_room = course_size // (len(active_rooms) if len(active_rooms) > 0 else 1)
            
            selected_pool = []
            for room in active_rooms: selected_pool += room[:target_per_room]
            remains = [item for room in active_rooms for item in room[target_per_room:]]
            random.shuffle(remains)
            needed = course_size - len(selected_pool)
            if needed > 0 and len(remains) >= needed: selected_pool += remains[:needed]
            
            random.shuffle(selected_pool)
            actual_size = min(course_size, len(selected_pool))
            
            if actual_size == 0: st.error("❌ クイズデータが見つかりません。")
            else:
                st.session_state.quiz_pool = selected_pool[:actual_size]
                st.session_state.c_index = 0
                st.session_state.c_score = 0
                st.session_state.last_feedback = None
                st.session_state.is_force_quit = False
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
            
    # メイン問題画面
    else:
        q = st.session_state.quiz_pool[st.session_state.c_index]
        idx = st.session_state.c_index
        total = len(st.session_state.quiz_pool)
        
        # 前回の結果表示
        if st.session_state.get('last_feedback'):
            fb = st.session_state.last_feedback
            if fb['correct']:
                st.success(f"⭕ 前問（第{idx}問）正解！ 答え: 【 {fb['ans']} 】")
            else:
                st.error(f"❌ 前問（第{idx}問）不正解... あなたの答え: 「{fb['user_ans']}」 / 正解: 【 {fb['ans']} 】")

        st.markdown(f"""
            <div style="background-color: #ffffff; border: 2px solid #222222; border-radius: 16px; padding: 24px 20px 20px 20px; position: relative; margin-top: 10px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
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

        # フォーム化によりEnterキー一発で送信・次へ進む構造を作成
        with st.form(key=f"quiz_form_{idx}"):
            user_ans = ""
            if q['type'] in ['text', 'fill_blank', 'image_text']:
                user_ans = st.text_input("解答を入力してEnterを押してください:", key=f"input_{idx}")
            elif q['type'] in ['choice', 'image_choice']:
                user_ans = st.radio("選択肢を選んでください:", q.get('pool', []), key=f"input_{idx}")
            elif q['type'] == 'text_multi':
                user_ans = st.text_input("解答（カンマ区切りで入力）:", key=f"input_{idx}")

            submitted = st.form_submit_button("回答して次の問題へ ➡️ (Enter)", use_container_width=True, type="primary")

            if submitted:
                is_correct = False
                ans_disp = " / ".join(q['correct']) if isinstance(q['correct'], list) else q['correct']

                if q['type'] == 'text_multi':
                    user_inputs = [norm(x) for x in user_ans.replace('、', ',').split(',') if norm(x) != ""]
                    correct_inputs = [norm(x) for x in q['correct']]
                    is_correct = (sorted(user_inputs) == sorted(correct_inputs))
                else:
                    is_correct = (norm(user_ans) == norm(q['correct']))

                if is_correct:
                    st.session_state.c_score += 1

                st.session_state.last_feedback = {
                    "correct": is_correct,
                    "user_ans": user_ans,
                    "ans": ans_disp
                }

                st.session_state.c_index += 1
                st.rerun()

        # 問題データ修正用ポップオーバー（画面下部）
        with st.popover("🛠️ この問題を即時修正する (Excel更新)", use_container_width=True):
            st.markdown("#### 📝 該当データの修正")
            source_file = q.get('source', '問題集.xlsx')
            row_i = q.get('row_idx', None)

            if source_file == '問題集.xlsx' and df_mondai is not None and row_i is not None:
                new_q = st.text_input("問題文:", value=str(df_mondai.at[row_i, 'question']), key=f"edit_q_{idx}")
                new_a = st.text_input("正解 (複数解答はカンマ区切り):", value=str(df_mondai.at[row_i, 'answer']), key=f"edit_a_{idx}")
                
                if st.button("💾 問題集.xlsx を上書き保存", key=f"save_mondai_{idx}"):
                    df_mondai.at[row_i, 'question'] = new_q
                    df_mondai.at[row_i, 'answer'] = new_a
                    df_mondai.to_excel("問題集.xlsx", sheet_name='Sheet1', index=False)
                    st.session_state.df_mondai = df_mondai
                    st.success("✅ 問題集.xlsx を正常に更新しました！")
                    st.rerun()

            elif source_file == 'character_master.xlsx' and df_master is not None and row_i is not None:
                c_name = st.text_input("名前:", value=str(df_master.at[row_i, 'name']), key=f"edit_name_{idx}")
                c_fruit = st.text_input("悪魔の実:", value=str(df_master.at[row_i, 'devil_fruit']) if pd.notna(df_master.at[row_i, 'devil_fruit']) else "", key=f"edit_fruit_{idx}")
                c_bday = st.text_input("誕生日:", value=str(df_master.at[row_i, 'birthday']) if pd.notna(df_master.at[row_i, 'birthday']) else "", key=f"edit_bday_{idx}")
                
                if st.button("💾 character_master.xlsx を上書き保存", key=f"save_master_{idx}"):
                    df_master.at[row_i, 'name'] = c_name
                    df_master.at[row_i, 'devil_fruit'] = c_fruit
                    df_master.at[row_i, 'birthday'] = c_bday
                    df_master.to_excel("character_master.xlsx", sheet_name='masterdata', index=False)
                    st.session_state.df_master = df_master
                    st.success("✅ character_master.xlsx を正常に更新しました！")
                    st.rerun()