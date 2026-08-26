# --- 1. ホーム画面 ---
elif selected == "ホーム":
    # フォルダから画像パスをランダムに取得
    all_imgs = (
        glob.glob("images/*.png")
        + glob.glob("images/*.jpg")
        + glob.glob("images/*.jpeg")
        + glob.glob("*.png")
        + glob.glob("*.jpg")
    )

    img_tags = ""
    if all_imgs:
        # ランダムに並び替えてHTML化（無限ループ用に同じ要素を2セット用意）
        sample_imgs = random.sample(all_imgs, min(len(all_imgs), 15))
        for img_path in sample_imgs * 2:
            try:
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    ext = img_path.split(".")[-1].lower()
                    mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                    img_tags += f'<img src="data:{mime};base64,{b64}" class="banner-img" />'
            except Exception:
                continue

    # 表題カードとカルーセルアニメーションのHTML/CSS
    banner_html = f"""
    <style>
    .title-card {{
        border: 2px solid #333;
        border-radius: 16px;
        padding: 35px 20px 25px 20px; /* 縦幅を大きく拡大 */
        text-align: center;
        background-color: rgba(255, 255, 255, 0.95);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        overflow: hidden;
        position: relative;
    }}
    .title-card h1 {{
        margin: 0 0 8px 0;
        font-size: 2.2rem;
        color: #111;
    }}
    .title-card p {{
        margin: 0 0 20px 0;
        color: #555;
        font-size: 1.05rem;
    }}
    
    /* 枠内画像スライダーエリア */
    .banner-slider-container {{
        width: 100%;
        overflow: hidden;
        position: relative;
        margin-top: 15px;
        border-top: 1px dashed #ccc;
        padding-top: 15px;
    }}
    .banner-track {{
        display: flex;
        width: max-content;
        animation: bannerScroll 30s linear infinite; /* 滑らかに連続アニメーション */
        gap: 12px;
    }}
    .banner-img {{
        width: 110px;
        height: 110px;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        flex-shrink: 0;
    }}
    @keyframes bannerScroll {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
    }}
    </style>

    <div class="title-card">
        <h1>🏴‍☠️ ONE PIECE ナレッジキング対策</h1>
        <p>最強のデータベースを脳に刻め</p>
        
        <div class="banner-slider-container">
            <div class="banner-track">
                {img_tags if img_tags else '<p style="color:#888;">（画像フォルダに画像を追加するとここに表示されます）</p>'}
            </div>
        </div>
    </div>
    """

    st.markdown(banner_html, unsafe_allow_html=True)
    st.write("")

    if df_all.empty:
        st.warning(
            "現在、読み込めるExcelデータ（.xlsx）がありません。GitHubにExcelファイルをアップロードしてください。"
        )
    else:
        st.info(
            f"👈 左側のメニューから機能を選択してください。（登録済データ: {len(df_all)} 件）"
        )
