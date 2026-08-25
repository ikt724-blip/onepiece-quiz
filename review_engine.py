import streamlit as st
import random
import os
from quiz_ui import display_quiz_ui

def norm(txt): return st.session_state.normalize_func(txt)

def render_review_page():
    if 'wrong_list' not in st.session_state or len(st.session_state.wrong_list) == 0:
        st.success("🎉 現在、苦手な問題（誤答ストック）はありません！")
        return

    if 'review_pool' not in st.session_state:
        unique_wrongs = []
        seen = set()
        for q in st.session_state.wrong_list:
            if q['question'] not in seen:
                seen.add(q['question'])
                unique_wrongs.append(q)
        random.shuffle(unique_wrongs)
        st.session_state.review_pool = unique_wrongs
        st.session_state.r_index = 0
        st.session_state.r_score = 0
        st.session_state.r_is_answered = False

    r_idx = st.session_state.r_index
    r_pool = st.session_state.review_pool
    r_total = len(r_pool)

    if r_idx >= r_total:
        st.balloons()
        st.success("🔥 苦手克服テスト終了！")
        if st.button("🧹 苦手ストックをすべて初期化", use_container_width=True):
            st.session_state.wrong_list = []
            if 'review_pool' in st.session_state: del st.session_state.review_pool
            st.rerun()
        return

    q = r_pool[r_idx]
    
    # 👑 復習モード用の超加速Enterハック
    if st.session_state.r_is_answered:
        st.markdown("<p style='color:#ff4b4b; font-weight:bold; margin-bottom:0;'>⬇️ そのまま【Enterキー】を叩けば、次の復習へ自動進軍！</p>", unsafe_allow_html=True)
        rev_next_trigger = st.text_input("復習ステルス", key=f"rev_trigger_{r_idx}", label_visibility="collapsed")
        if rev_next_trigger != "LOCK":
            st.session_state.r_index += 1
            st.session_state.r_is_answered = False
            st.session_state.sel_choice = None
            st.session_state.u_text = ""
            st.session_state.is_answered = False
            st.rerun()

    st.markdown(f"#### 🧠 復習第 {r_idx + 1} 問 / 全 {r_total} 問")
    st.info(q['question'])
    user_answered = st.session_state.r_is_answered

    if not user_answered: st.session_state.is_answered = False
    
    display_quiz_ui(q['type'], f"rev_{r_idx}", q, user_answered)

    if st.session_state.is_answered and not st.session_state.r_is_answered:
        st.session_state.r_is_answered = True
        
        is_current_correct = False
        if q['type'] in ['text', 'fill_blank', 'image_text']:
            alts = [norm(a) for a in q.get('alternatives', [])]
            is_current_correct = (norm(st.session_state.u_text) == norm(q['correct'])) or (norm(st.session_state.u_text) in alts)
        elif q['type'] == 'text_multi':
            is_current_correct = sorted([norm(x) for x in st.session_state.u_text]) == sorted([norm(x) for x in q['correct']])
        elif q['type'] == 'choice_multi':
            is_current_correct = sorted([norm(x) for x in st.session_state.sel_choice]) == sorted([norm(x) for x in q['correct']])
        elif q['type'] == 'matching':
            is_current_correct = all(norm(st.session_state.sel_choice.get(k, '')) == norm(v) for k, v in q.get('pairs', {}).items())
        elif q['type'] == 'sorting':
            is_current_correct = all(norm(st.session_state.sel_choice[r_i]) == norm(val) for r_i, val in enumerate(q['correct']))
        else:
            is_current_correct = (norm(st.session_state.sel_choice) == norm(q['correct']))

        if is_current_correct:
            st.session_state.r_score += 1
            st.session_state.wrong_list = [item for item in st.session_state.wrong_list if item['question'] != q['question']]
            st.success("⭕ リベンジ成功！苦手から除外されました！")
        else:
            st.error("❌ 不正解... 次こそは仕留めましょう。")
        st.rerun()

    if user_answered:
        if st.button("➡️ 次の復習問題へ進む (クリック用)", key=f"rev_click_nxt_{r_idx}", use_container_width=True):
            st.session_state.r_index += 1
            st.session_state.r_is_answered = False
            st.session_state.sel_choice = None
            st.session_state.u_text = ""
            st.session_state.is_answered = False
            st.rerun()
