import streamlit as st
import pandas as pd
import os

def render_search_page():
    st.title("🔍 AI検索モード")
    st.subheader("〜 キャラクターマスタ爆速逆引き図鑑 〜")
    st.write("---")

    df_master = st.session_state.df_master
    if df_master is None or df_master.empty:
        st.warning("⚠️ 『character_master.xlsx』がありません。")
        return

    search_keyword = st.text_input("検索キーワードを入力：", placeholder="ルフィ、5月5日、自然系 など")

    if search_keyword:
        mask = df_master.astype(str).apply(lambda x: x.str.contains(search_keyword, case=False, na=False)).any(axis=1)
        results_df = df_master[mask]

        if results_df.empty: st.error("❌ 一致するキャラクターは見つかりませんでした。")
        else:
            st.success(f"🏴‍☠️ {len(results_df)} 件のデータを統合サーチしました！")
            for _, row in results_df.iterrows():
                name, bday, fruit, f_type, img_file = str(row.get('name', '不明')), str(row.get('birthday', '不明')), str(row.get('devil_fruit', 'なし')), str(row.get('fruit_type', '---')), str(row.get('image', '')).strip()
                
                with st.container():
                    st.markdown(f'<div style="background-color: #f8f9fa; padding: 12px; border-radius: 12px; border-left: 5px solid #3498db; margin-bottom: 10px;"><b>🏴‍☠️ {name}</b></div>', unsafe_allow_html=True)
                    col_img, col_status = st.columns(2)
                    with col_img:
                        full_img_path = os.path.join("images", img_file)
                        if img_file and os.path.exists(full_img_path): st.image(full_img_path, width=150)
                        else: st.caption("NO IMAGE")
                    with col_status:
                        st.write(f"🎂 誕生日: {bday}\n\n🍇 悪魔の実: {fruit}\n\n📐 系統: {f_type}")
                    st.write("---")
