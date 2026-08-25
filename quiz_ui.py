import streamlit as st

def apply_knowledge_king_ui():
    """ナレッジキング風UIを全画面に強力強制適用するCSS"""
    st.markdown("""
    <style>
    /* 全体背景 */
    .stApp {
        background-color: #f4f5f7 !important;
        color: #111111 !important;
    }

    /* 4択選択肢ボタン */
    div[data-testid="stColumn"] button {
        background-color: #ffffff !important;
        color: #111111 !important;
        border: 2px solid #222222 !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        padding: 12px 8px !important;
    }
    div[data-testid="stColumn"] button:hover {
        background-color: #e2e8f0 !important;
        border-color: #000000 !important;
    }

    /* 入力フォーム枠 */
    div[data-testid="stTextInput"] input {
        background-color: #ffffff !important;
        color: #111111 !important;
        border: 2px solid #222222 !important;
        border-radius: 8px !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }

    /* 「決定」ボタン */
    .btn-submit button {
        background-color: #c58686 !important;
        color: #ffffff !important;
        border: 2px solid #9e5b5b !important;
        border-radius: 25px !important;
        font-size: 18px !important;
        font-weight: 900 !important;
    }

    /* 「パス」ボタン */
    .btn-pass button {
        background-color: #8c7853 !important;
        color: #ffffff !important;
        border: 2px solid #6b5b3e !important;
        border-radius: 25px !important;
        font-size: 14px !important;
        font-weight: 800 !important;
    }

    /* 「中断」ボタン */
    .btn-quit button {
        background-color: #6c757d !important;
        color: #ffffff !important;
        border: 2px solid #495057 !important;
        border-radius: 25px !important;
        font-size: 14px !important;
        font-weight: 800 !important;
    }

    /* 「修正」ボタン */
    .btn-edit button {
        background-color: #d97706 !important;
        color: #ffffff !important;
        border: 2px solid #b45309 !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def display_quiz_ui(q_type, idx, q, user_answered):
    apply_knowledge_king_ui()
    
    # 選択系問題（4択）
    if q_type in ['choice', 'image_choice']:
        choices = q.get('pool', [])
        if len(choices) >= 4:
            col1, col2 = st.columns(2)
            for i, opt in enumerate(choices[:4]):
                target_col = col1 if i % 2 == 0 else col2
                if target_col.button(opt, key=f"opt_{idx}_{i}", use_container_width=True, disabled=user_answered):
                    st.session_state.sel_choice = opt
                    st.rerun()
        else:
            for i, opt in enumerate(choices):
                if st.button(opt, key=f"opt_{idx}_{i}", use_container_width=True, disabled=user_answered):
                    st.session_state.sel_choice = opt
                    st.rerun()

    # 1択 記述問題
    elif q_type in ['text', 'fill_blank', 'image_text']:
        val = st.text_input("解答を入力:", value=st.session_state.u_text, key=f"input_{idx}", disabled=user_answered)
        st.session_state.u_text = val

    # 複数回答 記述問題（動的入力欄生成）
    elif q_type == 'text_multi':
        correct_list = q.get('correct', [])
        if not isinstance(st.session_state.u_text, list):
            st.session_state.u_text = [""] * len(correct_list)
        
        st.caption(f"📝 解答を {len(correct_list)} 個入力してください（順不同）:")
        for i in range(len(correct_list)):
            current_val = st.session_state.u_text[i] if i < len(st.session_state.u_text) else ""
            val = st.text_input(f"解答 {i+1}:", value=current_val, key=f"input_multi_{idx}_{i}", disabled=user_answered)
            if i < len(st.session_state.u_text):
                st.session_state.u_text[i] = val