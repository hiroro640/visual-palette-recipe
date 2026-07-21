import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import streamlit.components.v1 as components

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

# ============================================================
# デザインコンセプト：「印刷所のカラーチップ帳」
#   Paper   : #FAFAF7   Ink     : #16181C
#   Graphite: #767D87   Hairline: #E4E1D9
#   Accent  : ユーザーが選んだ色そのもの
# 見出し=Fraunces / 本文=Inter / データ=IBM Plex Mono
# ============================================================

st.set_page_config(page_title="Visual Palette Recipe", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    html, body, [data-testid='stSidebar'], [data-testid='stAppViewContainer'] {
        font-family: 'Inter', sans-serif;
        background-color: #FAFAF7;
        color: #16181C;
    }

    [data-testid='stSidebar'] {
        background-color: #F3F1EA;
        border-right: 1px solid #E4E1D9;
    }
    [data-testid='stSidebar'] > div:first-child {
        width: 340px !important;
    }
    [data-testid='stSidebar'][aria-expanded="true"] {
        width: 340px !important;
        min-width: 340px !important;
    }

    [data-testid='stHeader'] { background: transparent; }

    /* 余計な要素間の余白を詰めて、全体のリズムを揃える */
    div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {
        margin-bottom: 0.35rem;
    }

    /* ----- ヘッダー ----- */
    .studio-eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #767D87;
        margin-bottom: 6px;
    }
    .main-title {
        font-family: 'Fraunces', serif;
        font-size: 38px;
        font-weight: 600;
        letter-spacing: -0.5px;
        color: #16181C;
        line-height: 1.15;
        margin-bottom: 6px;
    }
    .main-subtitle {
        font-size: 14px;
        color: #767D87;
        margin-bottom: 4px;
    }
    .header-rule {
        border: none;
        border-top: 1px solid #E4E1D9;
        margin: 16px 0 22px 0;
    }

    .section-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #767D87;
        margin-bottom: 12px;
        margin-top: 2px;
    }
    .section-gap {
        height: 22px;
    }

    /* ----- サイドバー ----- */
    .sidebar-eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #767D87;
        margin-bottom: 2px;
    }
    .sidebar-title {
        font-family: 'Fraunces', serif;
        font-size: 22px;
        font-weight: 600;
        color: #16181C;
        margin-bottom: 16px;
    }
    .sidebar-field-label {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        line-height: 1.5;
        letter-spacing: 0.1px;
        color: #767D87;
        margin-bottom: 16px;
    }
    [data-testid='stSidebar'] hr {
        border-top: 1px solid #E4E1D9;
        margin: 18px 0;
    }

    /* ネイティブのカラーピッカーは隠さず、大きく上質に見せて直接使う（クリック1回） */
    [data-testid="stColorPicker"] label { display: none; }
    [data-testid="stColorPicker"] div[style*="background-color"] {
        width: 52px !important;
        height: 52px !important;
        border-radius: 12px !important;
        box-shadow: inset 0 0 0 1px rgba(22,24,28,0.15), 0 1px 3px rgba(22,24,28,0.08) !important;
    }
    .custom-readout {
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 52px;
    }
    .custom-readout .cs-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #767D87;
        margin-bottom: 3px;
    }
    .custom-readout .cs-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 16px;
        font-weight: 600;
        color: #16181C;
    }

    /* ----- 💳 カラーチップカード（Pantone風スウォッチ） ----- */
    .colorhunt-pure-card {
        border-radius: 3px;
        overflow: hidden;
        background: #FFFFFF;
        box-shadow: 0 1px 3px rgba(22,24,28,0.06);
        border: 1px solid #E4E1D9;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        position: relative;
    }

    /* 選択中は見本帳から一枚引き抜いたように少し持ち上がる（枠は灰色） */
    .colorhunt-pure-card.active {
        transform: translateY(-6px);
        box-shadow: 0 14px 26px rgba(22,24,28,0.14);
        border-color: #9AA1AB;
        border-width: 1.5px;
    }

    .pure-punch {
        position: absolute;
        top: 8px;
        right: 8px;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #FAFAF7;
        box-shadow: inset 0 0 0 1px rgba(22,24,28,0.15);
        z-index: 2;
    }

    .pure-meta {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10.5px;
        font-weight: 500;
        letter-spacing: 1.5px;
        padding: 9px 12px;
        color: #A7ACB4;
        background: #FFFFFF;
        text-align: left;
        text-transform: uppercase;
        border-bottom: 1px solid transparent;
    }
    .colorhunt-pure-card.active .pure-meta {
        color: #16181C;
        font-weight: 600;
        background: #FFFFFF;
        border-bottom: 1px solid #E4E1D9;
    }

    .pure-bar {
        display: flex;
        width: 100%;
        height: 46px;
    }

    .pure-block {
        height: 100%;
        position: relative;
        box-sizing: border-box;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05);
    }

    .pure-indicator {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 9px;
        height: 9px;
        background-color: #FFFFFF;
        border-radius: 50%;
        box-shadow: 0 0 0 2px rgba(22,24,28,0.55);
    }

    /* ----- 🖼️🍩 ポスター × パレット：ひとつのカードにまとめた見開き構成 ----- */
    .st-key-spread_card [data-testid="stVerticalBlockBorder"] {
        background: #FFFFFF !important;
        border: 1px solid #E4E1D9 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(22,24,28,0.05) !important;
        padding: 28px !important;
    }
    .st-key-spread_card [data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-of-type {
        border-right: 1px solid #E4E1D9;
        padding-right: 30px !important;
    }
    .st-key-spread_card [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-of-type {
        padding-left: 30px !important;
    }

    .pane-eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10.5px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #A7ACB4;
        margin-bottom: 14px;
    }

    .poster-caption {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: #A7ACB4;
        margin-top: 12px;
        letter-spacing: 0.3px;
    }

    /* 画像・グラフにマウスを乗せた時に出るツールバー（余計な四角の原因になりやすい）を非表示 */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }

    div[data-testid="column"] { padding-left: 6px; padding-right: 6px; }

    /* ----- 📱 レスポンシブ対応（スマホ幅） -----
       Streamlitのcolumnsは基本的に自動で折り返すが、確実性のため
       flex-wrapとmin-widthを明示的に指定して確実にスタックさせる */
    @media (max-width: 680px) {
        [data-testid='stSidebar'] > div:first-child {
            width: 86vw !important;
            max-width: 340px !important;
        }
        [data-testid='stSidebar'][aria-expanded="true"] {
            width: 86vw !important;
            max-width: 340px !important;
            min-width: 0 !important;
        }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            row-gap: 20px;
        }
        div[data-testid="column"] {
            min-width: 100% !important;
            flex: 1 1 100% !important;
            width: 100% !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        .main-title {
            font-size: 26px;
        }
        .main-subtitle {
            font-size: 13px;
        }
        .studio-eyebrow {
            font-size: 10px;
            letter-spacing: 2px;
        }
        .header-rule {
            margin: 12px 0 16px 0;
        }
        .section-label {
            font-size: 10px;
            letter-spacing: 1.5px;
            margin-bottom: 12px;
            margin-top: 22px;
        }
        .section-gap {
            height: 24px;
        }
        [data-testid="stVerticalBlockBorder"] {
            padding: 16px !important;
        }
        .pure-bar {
            height: 40px;
        }
        .pure-meta {
            font-size: 10px;
            padding: 8px 10px;
        }
        .colorhunt-pure-card.active {
            transform: translateY(-3px);
        }
        [data-testid="stColorPicker"] div[style*="background-color"] {
            width: 44px !important;
            height: 44px !important;
        }
        .sidebar-title {
            font-size: 19px;
        }
        .poster-caption {
            font-size: 10px;
        }
        .st-key-spread_card [data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-of-type {
            border-right: none;
            border-bottom: 1px solid #E4E1D9;
            padding-right: 0 !important;
            padding-bottom: 22px !important;
            margin-bottom: 22px !important;
        }
        .st-key-spread_card [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-of-type {
            padding-left: 0 !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="studio-eyebrow">Palette Studio · Prototype</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">Visual Palette Recipe</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">ポスターから抽出した配色を、印刷所のカラーチップ帳のようにめくって探す。</div>', unsafe_allow_html=True)
st.markdown('<hr class="header-rule" />', unsafe_allow_html=True)

# クエリパラメータによる状態管理へ移行（表示バグの原因となるダサいUI要素を完全に排除するため）
query_params = st.query_transform() if hasattr(st, "query_transform") else st.query_params
if 'recipe_idx' in query_params:
    try:
        st.session_state.poster_idx = int(query_params['recipe_idx'])
    except:
        st.session_state.poster_idx = 0
elif 'poster_idx' not in st.session_state:
    st.session_state.poster_idx = 0

# 候補カードのクリックはブラウザの本当のページ遷移（フルリロード）になるため、
# session_stateだけに色を保存していると初期色にリセットされてしまう。
# そこで選択中の色もURLクエリに乗せて、遷移後も同じ色を復元する。
if 'picked_color' not in st.session_state:
    default_color = '#3B82F6'
    if 'color' in query_params:
        candidate = str(query_params['color'])
        if len(candidate) == 6:
            try:
                int(candidate, 16)
                default_color = '#' + candidate.upper()
            except ValueError:
                pass
    st.session_state.picked_color = default_color

# --- 2. 🧭 サイドバー ---
with st.sidebar:
    st.markdown('<div class="sidebar-eyebrow">Scout Color</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">🔍 スカウトカラー</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-field-label">色をクリックして選ぶと、近い配色のポスターが自動で表示されます</div>',
        unsafe_allow_html=True
    )

    current_hex = st.session_state.picked_color.upper()

    # 正確な色をワンクリックでネイティブのピッカーから直接選ぶ
    swatch_col, info_col = st.columns([1, 2.4])
    with swatch_col:
        st.color_picker("色を選択", key="picked_color", label_visibility="collapsed")
    with info_col:
        readout_hex = st.session_state.picked_color.upper()
        st.markdown(
            f'<div class="custom-readout"><span class="cs-label">Current Pigment</span>'
            f'<span class="cs-value">{readout_hex}</span></div>',
            unsafe_allow_html=True
        )

    picked_color = st.session_state.picked_color
    user_rgb = np.array([int(picked_color[1:3], 16), int(picked_color[3:5], 16), int(picked_color[5:7], 16)])

    st.markdown('<hr/>', unsafe_allow_html=True)
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

        st.markdown('<div class="section-label">Swatch Deck — 近いレシピ一覧</div>', unsafe_allow_html=True)

        # 🔄 画面上の不要な残骸ボタンを絶対に生成しないクリック手法
        btn_cols = st.columns(len(recs))
        for i, rec in enumerate(recs):
            with btn_cols[i]:
                num_colors = int(rec["row"]['num_actual_colors'])
                is_active = i == st.session_state.poster_idx
                active_class = "active" if is_active else ""
                label_text = f"● No.{i+1:02d}" if is_active else f"No.{i+1:02d}"

                card_html = f'<div class="colorhunt-pure-card {active_class}">'
                card_html += '<div class="pure-punch"></div>'
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

                st.markdown(f"""
                    <a href="?recipe_idx={i}&color={picked_color[1:]}" target="_self" style="text-decoration: none; color: inherit; display: block;">
                        {card_html}
                    </a>
                """, unsafe_allow_html=True)

        st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

        # 【ポスター × カラーレシピ】を1枚の見開きカードにまとめる
        img_path = os.path.join("image", current_row['filename'])

        num_colors = int(current_row['num_actual_colors'])
        colors, ratios = [], []
        for i in range(1, num_colors + 1):
            rgb = [int(current_row[f'color{i}_r']), int(current_row[f'color{i}_g']), int(current_row[f'color{i}_b'])]
            colors.append('#%02x%02x%02x' % tuple(rgb))
            ratios.append(int(current_row[f'ratio{i}'] * 100))

        labels = [f" {hex_c.upper()} ({pct}%)" for hex_c, pct in zip(colors, ratios)]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=ratios,
            hole=.62,
            domain=dict(x=[0, 0.56], y=[0.06, 0.94]),
            marker=dict(colors=colors, line=dict(color='#FFFFFF', width=3)),
            textinfo='none',
            sort=False,
            direction='clockwise'
        )])
        fig.update_layout(
            showlegend=True,
            legend=dict(
                font=dict(family="IBM Plex Mono, monospace", size=12.5, color="#16181C"),
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=0.66,
                itemwidth=30,
                traceorder="normal",
                entrywidthmode="fraction",
                entrywidth=0.45
            ),
            font=dict(family="Inter, sans-serif", color="#16181C"),
            height=220,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        with st.container(border=True, key="spread_card"):
            col_img, col_chart = st.columns([0.85, 1.15], gap="large")

            with col_img:
                st.markdown('<div class="pane-eyebrow">Source Poster</div>', unsafe_allow_html=True)
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    st.info(f"画像が `image/{current_row['filename']}` に見つかりません。")
                st.markdown(f'<p class="poster-caption">{current_row["filename"]}</p>', unsafe_allow_html=True)

            with col_chart:
                st.markdown('<div class="pane-eyebrow">Color Recipe</div>', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    else:
        st.warning("一致するポスターがありませんでした。")

except FileNotFoundError:
    st.error("posters_dataset.csv が見つかりません。先に phase2.py を動かしてください。")
