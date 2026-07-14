import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

def find_matches(user_rgb, df, top_n=5):
    matches = []
    for _, row in df.iterrows():
        min_dist = float('inf')
        hit_color_idx = 1
        num_colors = int(row['num_actual_colors'])
        for i in range(1, num_colors + 1):
            p_rgb = np.array([row[f'color{i}_r'], row[f'color{i}_g'], row[f'color{i}_b']])
            dist = np.linalg.norm(user_rgb - p_rgb)
            if dist < min_dist:
                min_dist = dist
                hit_color_idx = i
        matches.append({"dist": min_dist, "row": row, "hit_color_idx": hit_color_idx})
    matches.sort(key=lambda x: x["dist"])
    return matches[:top_n]

# --- UI全体の設定と、ノイズを極限まで削った引き算のCSS ---
st.set_page_config(page_title="Visual Palette Recipe", layout="wide")

# 💡 ダークモード強制防止：背景とベース文字色をライトモード（白・グレー）に固定するスタイル
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=300;400;500;600&display=swap');
    
    /* アプリ全体、メインエリア、サイドバーの背景色・文字色を完全強制指定（ダークモード対策） */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #F7F9FA !important;
        color: #2D3748 !important;
    }
    
    /* サイドバー内部要素のテキスト色をダークモード時でも黒系に固定 */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] span {
        color: #2D3748 !important;
    }
    
    /* メインタイトル */
    .main-title {
        font-size: 28px;
        font-weight: 600;
        letter-spacing: -0.5px;
        color: #1A202C !important;
        margin-bottom: 2px;
    }
    
    .section-label {
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #718096 !important;
        margin-bottom: 12px;
        margin-top: 16px;
    }

    /* すべての囲み枠・不要なシャドウを完全消去 */
    div[data-testid="stVerticalBlockBorder"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0px !important;
    }

    /* 💡 ピュア・パレット：灰色の外枠（border）を完全排除 */
    .colorhunt-pure-card {
        border-radius: 12px;
        overflow: hidden;
        background: #FFFFFF !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02);
        border: none !important; /* 枠線は絶対に描かない */
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    /* 選択中（active）であっても枠線は出さず、わずかな浮遊感だけで表現 */
    .colorhunt-pure-card.active {
        transform: translateY(-3px);
        box-shadow: 0 10px 24px rgba(0,0,0,0.06);
    }
    
    .pure-meta {
        font-size: 11px;
        font-weight: 500;
        padding: 8px 12px;
        color: #A0AEC0 !important; /* 非選択時は薄いグレー */
        background: #FFFFFF !important;
        text-align: left;
    }
    .colorhunt-pure-card.active .pure-meta {
        color: #2D3748 !important; /* 選択中だけ文字がハッキリ浮かび上がる */
        font-weight: 600;
        background: #F1F5F9 !important;
    }
    
    .pure-bar {
        display: flex;
        width: 100%;
        height: 42px;
    }
    
    /* 白埋もれ対策 */
    .pure-block {
        height: 100%;
        position: relative;
        box-sizing: border-box;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05);
    }
    
    /* スカウトピン */
    .pure-indicator {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 10px;
        height: 10px;
        background-color: #FFFFFF !important;
        border-radius: 50%;
        box-shadow: 0 0 0 2px rgba(0,0,0,0.5);
    }

    /* 🎯 ユーザーフレンドリーなカラーピッカーボード */
    .color-status-board {
        padding: 14px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-family: 'monospace';
        font-size: 16px;
        letter-spacing: 0.5px;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.1);
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎨 Visual Palette Recipe</div>', unsafe_allow_html=True)
st.caption("Color Huntのミニマリズムを纏った配色パレットジェネレーター (Prototype)")

# --- 1. 🧭 URLパラメータから状態を復元（ブラウザのリロード対策） ---
query_params = st.query_params

# URLに色情報があればそれを使う。なければデフォルトの青(#3B82F6)
if 'color' in query_params:
    default_color = "#" + query_params['color']
else:
    default_color = "#3B82F6"

# URLにレシピ番号があればそれを使う。なければ最初のレシピ(0)
if 'recipe_idx' in query_params:
    try:
        st.session_state.poster_idx = int(query_params['recipe_idx'])
    except:
        st.session_state.poster_idx = 0
else:
    st.session_state.poster_idx = 0

# --- 2. 🧭 サイドバー ---
with st.sidebar:
    st.write("### 🔍 スカウトカラー")
    picked_color = st.color_picker("探したい色を直感的に選択", default_color)
    
    # 💡 重要なバグ修正：もしカラーピッカーで新しい色が選ばれたら、URLパラメータを更新して強制再描画！
    if picked_color != default_color:
        clean_hex = picked_color.replace('#', '')
        st.query_params.update(color=clean_hex, recipe_idx=0)
        st.rerun()
            
    user_rgb = np.array([int(picked_color[1:3], 16), int(picked_color[3:5], 16), int(picked_color[5:7], 16)])
    
    r, g, b = user_rgb
    text_color = "#FFFFFF" if (r*0.299 + g*0.587 + b*0.114) < 186 else "#1A202C"
    st.markdown(f'<div class="color-status-board" style="background-color: {picked_color}; color: {text_color};">CURRENT: {picked_color.upper()}</div>', unsafe_allow_html=True)
    
    st.write("---")
    st.caption("※2%以下の細かなカラーノイズは自動で除外され、主要な配色比率のみが抽出されます。")

# --- 3. 🎬 メインコンテンツエリア ---
try:
    df = pd.read_csv("posters_dataset.csv")
    recs = find_matches(user_rgb, df)

    if recs:
        # インデックス範囲外エラーを完全に防止
        if st.session_state.poster_idx >= len(recs):
            st.session_state.poster_idx = 0
            
        current_match = recs[st.session_state.poster_idx]
        current_row = current_match["row"]
        
        st.write("")
        
        # 🔄 画面上の不要な残骸ボタンを絶対に生成しないクリック手法
        btn_cols = st.columns(len(recs))
        for i, rec in enumerate(recs):
            with btn_cols[i]:
                num_colors = int(rec["row"]['num_actual_colors'])
                is_active = i == st.session_state.poster_idx
                active_class = "active" if is_active else ""
                label_text = f"● RECIPE {i+1}" if is_active else f"RECIPE {i+1}"
                
                # パレットの見た目をピュアHTMLで構築（灰色の外枠は存在しない）
                card_html = f'<div class="colorhunt-pure-card {active_class}">'
                card_html += f'<div class="pure-meta">{label_text}</div>'
                card_html += '<div class="pure-bar">'
                
                for c_idx in range(1, num_colors + 1):
                    pr = int(rec["row"][f'color{c_idx}_r'])
                    pg = int(rec["row"][f'color{c_idx}_g'])
                    pb = int(rec["row"][f'color{c_idx}_b'])
                    hex_c = '#%02x%02x%02x' % (pr, pg, pb)
                    pct = rec["row"][f'ratio{c_idx}'] * 100
                    
                    indicator_markup = '<div class="pure-indicator"></div>' if c_idx == rec["hit_color_idx"] else ''
                    card_html += f'<div class="pure-block" style="background-color: {hex_c}; width: {pct}%;">{indicator_markup}</div>'
                card_html += '</div></div>'
                
                # 💡 重要なバグ修正：リンク遷移先URLに「選択中の色情報」も付与する
                clean_color_hex = picked_color.replace('#', '')
                st.markdown(f"""
                    <a href="?recipe_idx={i}&color={clean_color_hex}" target="_self" style="text-decoration: none; color: inherit; display: block;">
                        {card_html}
                    </a>
                """, unsafe_allow_html=True)
                    
        st.write("---")
        
        # 【左：原画ポスター】 と 【右：洗練されたドーナツグラフ】
        col_img, col_chart = st.columns([1, 1])
        
        with col_img:
            st.markdown('<div class="section-label">🖼️ Source Poster</div>', unsafe_allow_html=True)
            img_path = os.path.join("image", current_row['filename'])
            
            if os.path.exists(img_path):
                st.image(img_path, width=340)
            else:
                st.info(f"画像が `image/{current_row['filename']}` に見つかりません。")
            st.markdown('<p style="font-size:11px; color:#A0AEC0; margin-top:8px; font-family: monospace;">%s</p>' % current_row['filename'], unsafe_allow_html=True)
                
        with col_chart:
            st.markdown('<div class="section-label">🍩 Color Recipe Donut</div>', unsafe_allow_html=True)
            
            num_colors = int(current_row['num_actual_colors'])
            colors, ratios, labels = [], [], []
            
            for i in range(1, num_colors + 1):
                rgb = [int(current_row[f'color{i}_r']), int(current_row[f'color{i}_g']), int(current_row[f'color{i}_b'])]
                hex_c = '#%02x%02x%02x' % tuple(rgb)
                ratio_pct = int(current_row[f'ratio{i}'] * 100)
                
                colors.append(hex_c)
                ratios.append(ratio_pct)
                labels.append(f" {hex_c.upper()} ({ratio_pct}%)")
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=ratios,
                hole=.45, 
                marker=dict(
                    colors=colors,
                    line=dict(color='#F7F9FA', width=3)
                ),
                textinfo='percent',
                sort=False,
                direction='clockwise'
            )])
            
            fig.update_layout(
                showlegend=True,
                legend=dict(
                    font=dict(family="monospace", size=15, color="#1A202C", weight="bold"),
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02
                ),
                height=350,
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.warning("一致するポスターがありませんでした。")
        
except FileNotFoundError:
    st.error("posters_dataset.csv が見つかりません。先に phase2.py を動かしてください。")
