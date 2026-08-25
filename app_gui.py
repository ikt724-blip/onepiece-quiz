import streamlit as st
import pandas as pd
import os
import unicodedata
from streamlit_option_menu import option_menu
import qrcode
from pyngrok import ngrok, conf
import io

# 1. ページの初期設定
st.set_page_config(
    page_title="ONE PIECE ナレッジキング対策", 
    page_icon="🏴‍☠️", 
    layout="centered"
)

# 2. 表記揺れ（ヴァ/バ、ヴ/ブ、・、空白など）を完全吸収する正規化関数
def normalize_string(text):
    if not text: return ""
    text = unicodedata.normalize('NFKC', str(text)).lower().strip()
    # 読み表記の揺れを統一
    replace_dict = {
        "ヴァ": "バ", "ヴィ": "ビ", "ヴ": "ブ", "ヴェ": "ベ", "ヴォ": "ボ",
        "・": "", " ": "", " ": "", ".": "", "（": "", "）": "", "(": "", ")": "", "-": "", "ー": ""
    }
    for k, v in replace_dict.items():
        text = text.replace(k, v)
    return text

if 'normalize_func' not in st.session_state:
    st.session_state.normalize_func = normalize_string

# 3. Excelデータ読込
def load_data(file_path, sheet_name='masterdata'):
    if not os.path.exists(file_path): return None
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except: return None

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data("character_master.xlsx", 'masterdata')
if 'df_mondai' not in st.session_state:
    st.session_state.df_mondai = load_data("問題集.xlsx", 'Sheet1')

if 'nav_index' not in st.session_state:
    st.session_state.nav_index = 0

# 4. 外出先連携
@st.cache_resource
def start_secure_tunnel():
    try:
        conf.get_default().auth_token = "3HfrNxRmXChhrdAGXP4TvqOY6aN_7ki2FSoque5BRZJEER81V"
        tunnels = ngrok.get_tunnels()
        for t in tunnels: ngrok.disconnect(t.public_url)
        public_url = ngrok.connect(8501).public_url
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(public_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return public_url, buf.getvalue()
    except: return None, None

public_url, qr_image_bytes = start_secure_tunnel()

# 5. サイドメニュー
with st.sidebar:
    st.markdown("<h2 style='color: #ffffff; font-size: 18px; font-weight: 900;'>🏴‍☠️ ナビセンター</h2>", unsafe_allow_html=True)
    current_mode = option_menu(
        menu_title=None,
        options=["ホーム", "テスト開始", "苦手克服", "AI検索モード", "データ追加"],
        icons=["house", "sword", "brain", "search", "plus-circle"],
        menu_icon="cast", 
        default_index=st.session_state.nav_index,
        key="main_menu_option"
    )
    
    st.write("---")
    if qr_image_bytes:
        st.caption("📱 モバイル連携QR")
        st.image(qr_image_bytes, use_container_width=True)

# 6. 画面ルーティング
if current_mode == "ホーム":
    st.markdown("""
        <div style="background:#fff; border:2px solid #222; border-radius:16px; padding:20px; text-align:center;">
            <h2 style="color:#111; font-weight:900; margin:0;">🏴‍☠️ ONE PIECE ナレッジキング対策</h2>
            <p style="color:#666; margin-top:5px;">最強のデータベースを脳に刻め</p>
        </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.info("👈 左側のメニューから『テスト開始』を選択してクイズに挑戦してください！")

elif current_mode == "テスト開始":
    from quiz_engine import render_quiz_page
    render_quiz_page()

elif current_mode == "苦手克服":
    from review_engine import render_review_page
    render_review_page()

elif current_mode == "AI検索モード":
    from search_engine import render_search_page
    render_search_page()

elif current_mode == "データ追加":
    from editor_engine import render_editor_page
    render_editor_page()