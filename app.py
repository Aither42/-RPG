from __future__ import annotations

import html
import time
import streamlit as st

from game.engine import (
    ACT_LABELS,
    TOTAL_TURNS,
    active_character_cards,
    choose,
    ensure_scene,
    new_game,
    options_for_scene,
    owned_techniques,
)

st.set_page_config(
    page_title="都市武俠：我的公司好像是邪教",
    page_icon="🥋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root{
    --ink:#15110d;
    --panel:#241b14;
    --paper:#f6ead0;
    --muted:#b8a781;
    --bronze:#b58a4a;
    --bronze2:#876339;
    --red:#8f2f26;
}
[data-testid="stAppViewContainer"]{
    background:
        radial-gradient(circle at 20% 0%, rgba(181,138,74,.07), transparent 30%),
        linear-gradient(180deg,#15110d 0%,#19130f 55%,#120f0c 100%) !important;
    color:var(--paper) !important;
}
[data-testid="stMainBlockContainer"]{
    max-width:520px !important;
    padding-top:.62rem !important;
    padding-bottom:1.2rem !important;
}
header,footer{visibility:hidden;height:0}
html,body,[class*="css"],.stMarkdown,p,li,label,span,div{
    font-family:"Noto Serif TC","Songti TC","PMingLiU","MingLiU",serif;
}
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li{
    color:var(--paper) !important;
}
.game-title{
    color:#fff3d2 !important;
    font-size:1.2rem;
    font-weight:900;
    letter-spacing:.045em;
    margin-bottom:.12rem;
}
.game-subtitle{
    color:var(--muted) !important;
    font-size:.86rem;
    margin-bottom:.35rem;
}
.scene-card{
    border:1px solid var(--bronze2);
    border-radius:14px;
    padding:1rem;
    background:linear-gradient(180deg,#2b2017,#1e1712);
    box-shadow:0 7px 22px rgba(0,0,0,.23);
    margin:.6rem 0;
}
.scene-speaker{color:#d9bd82 !important;font-size:.82rem;margin-bottom:.35rem}
.scene-title{color:#fff0c8 !important;font-size:1.08rem;font-weight:900;margin-bottom:.55rem}
.scene-body{color:#f7edda !important;line-height:1.78;font-size:1rem;white-space:pre-wrap}
.result-card{
    border-left:4px solid var(--bronze);
    border:1px solid #4e3c28;
    border-left-width:4px;
    padding:.72rem .86rem;
    margin:.45rem 0 .65rem 0;
    background:#201812;
    border-radius:10px;
    color:#f5ead3 !important;
    line-height:1.65;
}
.gain-card{
    border:1px solid #9b7a41;
    background:#292012;
    color:#ffe8a6 !important;
    border-radius:10px;
    padding:.68rem .82rem;
    margin:.45rem 0;
}
.dialogue-wrap{
    border:1px solid #8d6a3a;
    border-left:4px solid var(--red);
    background:linear-gradient(180deg,#211912,#17110d);
    border-radius:12px;
    padding:.65rem .86rem;
    margin:.5rem 0 .75rem 0;
}
.dialogue-kicker{color:#9d8965 !important;font-size:.72rem;letter-spacing:.12em;margin-bottom:.2rem}
.dialogue-line{padding:.42rem 0 .48rem 0;border-bottom:1px solid rgba(181,138,74,.17)}
.dialogue-line:last-child{border-bottom:none}
.dialogue-speaker{color:#d8ab5d !important;font-size:.78rem;font-weight:900;letter-spacing:.065em;margin-bottom:.18rem}
.dialogue-text{color:#fff3d6 !important;font-size:1.01rem;line-height:1.66;font-weight:650}
.dialogue-player .dialogue-speaker{color:#bdb08f !important}
.dialogue-player .dialogue-text{color:#eadfc8 !important}
.dialogue-narration .dialogue-speaker{color:#8f8064 !important}
.dialogue-narration .dialogue-text{color:#cdbf9e !important;font-style:italic;font-weight:500}
div.stButton > button,
button[kind="secondary"],
button[kind="primary"]{
    width:100% !important;
    min-height:3.12rem !important;
    border-radius:11px !important;
    text-align:left !important;
    justify-content:flex-start !important;
    white-space:normal !important;
    line-height:1.42 !important;
    background:linear-gradient(180deg,#2d2117,#211811) !important;
    color:#fff0cf !important;
    border:1px solid #8d6a3a !important;
}
div.stButton > button p,
div.stButton > button span,
button[kind="secondary"] p,
button[kind="secondary"] span,
button[kind="primary"] p,
button[kind="primary"] span{color:#fff0cf !important}
[data-testid="stPopover"] button{
    background:#2a2017 !important;
    color:#f6e7c4 !important;
    border:1px solid #83643a !important;
    min-height:2.3rem !important;
    border-radius:10px !important;
}
[data-testid="stPopover"] button p,
[data-testid="stPopover"] button span{color:#f6e7c4 !important}
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
[data-testid="stPopoverBody"],
[data-testid="stPopoverBody"] > div,
[role="dialog"]{
    background:#241b14 !important;
    color:#f5e7c6 !important;
    border-color:#8b6a3e !important;
}
div[data-baseweb="popover"] *,
[data-testid="stPopoverBody"] *,
[role="dialog"] *{color:#f5e7c6 !important}
input,textarea,[data-baseweb="input"] > div{
    background:#211811 !important;
    color:#f7ebd2 !important;
    border-color:#765936 !important;
}
[data-testid="stProgress"] > div > div{background:#2a2017 !important}
[data-testid="stProgress"] > div > div > div{
    background:linear-gradient(90deg,#7c2d24,#b58a4a) !important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] *{color:#aa9a79 !important}
hr{border-color:#4e3b27 !important}
</style>
""",
    unsafe_allow_html=True,
)


def render_brand(subtitle=None):
    st.markdown(
        '<div class="game-title">🥋 都市武俠：我的公司好像是邪教</div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f'<div class="game-subtitle">{html.escape(subtitle)}</div>',
            unsafe_allow_html=True,
        )


def render_dialogue(lines):
    box = st.empty()
    shown = []
    for line in lines:
        shown.append(line)
        blocks = ['<div class="dialogue-kicker">上一幕・人物回應</div>']
        for item in shown:
            kind = item.get("kind", "npc")
            css = "dialogue-line"
            if kind == "player":
                css += " dialogue-player"
            elif kind == "narration":
                css += " dialogue-narration"
            blocks.append(
                '<div class="' + css + '">'
                '<div class="dialogue-speaker">'
                + html.escape(str(item.get("speaker", "")))
                + '</div><div class="dialogue-text">'
                + html.escape(str(item.get("text", "")))
                + '</div></div>'
            )
        box.markdown(
            '<div class="dialogue-wrap">' + "".join(blocks) + "</div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.5 if kind == "player" else 0.72 if kind == "narration" else 0.88)


if "game" not in st.session_state:
    render_brand("手機短篇互動小說｜15 個主要決策｜約 15～25 分鐘")
    st.markdown("---")
    st.write(
        "你只是來報到的新人。但每一次重新開始，第一天遇到的怪事都可能不同："
        "可能是辭職符、飛劍停車格、會說話的祖師 AI，甚至是比你更早打卡的影子。"
    )
    player_name = st.text_input("你的名字", value="新人", max_chars=12)
    if st.button("開始第一天報到", type="primary", use_container_width=True):
        recent = st.session_state.get("recent_openings", [])
        st.session_state.game = new_game(
            player_name,
            avoid_openings=recent,
        )
        opening = st.session_state.game.get("opening_family", "")
        if opening:
            st.session_state.recent_openings = (recent + [opening])[-4:]
        st.rerun()
    st.stop()

game = st.session_state.game

if game.get("ending"):
    render_brand("本局已結束")
    ending = game["ending"]

    st.markdown(
        '<div class="scene-card">'
        f'<div class="scene-title">{html.escape(ending["title"])}</div>'
        f'<div class="scene-body">{html.escape(ending["body"]).replace(chr(10), "<br>")}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.write("**你最後揭開的核心秘密：** " + ending["secret_title"])
    st.write(
        f"**本局學會功法：** {len(game['techniques'])} 門　　"
        f"**找到線索：** {len(game['clues'])} 條"
    )

    st.markdown("### 🏆 本局成就")
    for achievement in ending.get("achievements", []):
        st.markdown(
            f"**{achievement['title']}**  \n"
            f"{achievement['description']}"
        )

    signature = ending.get("signature_technique", {})
    if signature:
        st.markdown("### 🥋 你融會貫通出的獨門功法")
        st.markdown(
            '<div class="gain-card">'
            f"<b>{html.escape(signature.get('name',''))}</b><br>"
            f"{html.escape(signature.get('description',''))}"
            "</div>",
            unsafe_allow_html=True,
        )

    if ending.get("epilogue"):
        st.markdown("### 📜 後日奇聞")
        st.markdown(
            '<div class="result-card">'
            + html.escape(ending["epilogue"])
            + "</div>",
            unsafe_allow_html=True,
        )

    if st.button(
        "重新報到，開始另一條世界線",
        type="primary",
        use_container_width=True,
    ):
        del st.session_state.game
        st.rerun()

    st.stop()

scene = ensure_scene(game)

render_brand(
    f"{ACT_LABELS[scene['act']]}　｜　第 {min(game['turn'] + 1, TOTAL_TURNS)}/{TOTAL_TURNS} 個決定"
)
st.progress(game["turn"] / TOTAL_TURNS)

if game.get("dialogue_pending") and game.get("dialogue_queue"):
    render_dialogue(game["dialogue_queue"])
    game["dialogue_pending"] = False
    st.session_state.game = game

c1, c2, c3 = st.columns(3)

with c1:
    with st.popover("👥 人物", use_container_width=True):
        for item in active_character_cards(game):
            st.markdown(
                f"**{item['name']}｜{item['job']}**  \n"
                f"關係：{item['relationship']}｜情緒：{item['emotion']}  \n"
                f"{item['hook']}  \n"
                f"**個性：** {item['personality']}  \n"
                f"**成長背景：** {item['background']}  \n"
                f"**想要的事：** {item['desire']}  \n"
                f"**最怕的事：** {item['fear']}  \n"
                f"**軟肋：** {item['soft_spot']}"
            )
            st.markdown("---")

with c2:
    with st.popover("🥋 功法", use_container_width=True):
        techniques = owned_techniques(game)
        if not techniques:
            st.caption("還沒有功法。它們會從對話選項與事件中突然出現。")
        for technique in techniques:
            status = f"已使用 {technique.get('use_count', 0)} 次"
            if technique.get("countered"):
                status += "｜⚠️ NPC 已研究反制"
            st.markdown(
                f"**《{technique['name']}》**  \n"
                f"{technique['description']}  \n"
                f"_{status}_"
            )
            if technique.get("persistent_effect"):
                st.caption("餘波：" + technique["persistent_effect"])

with c3:
    with st.popover("🔎 線索", use_container_width=True):
        if not game["clues"]:
            st.caption("目前只有一種感覺：這公司真的不太正常。")
        for clue in game["clues"][-6:]:
            st.markdown("• " + clue)

if game.get("last_gain"):
    st.markdown(
        '<div class="gain-card">'
        + html.escape(game["last_gain"])
        + "</div>",
        unsafe_allow_html=True,
    )

if game.get("last_result"):
    st.markdown(
        '<div class="result-card"><b>剛才造成的結果</b><br>'
        + html.escape(game["last_result"]).replace("\n", "<br>")
        + "</div>",
        unsafe_allow_html=True,
    )

focus = game["active_characters"].get(scene["focus_role"])
speaker = (
    f"{focus['short_name']}｜{focus['job']}"
    if focus
    else "公司內部"
)

st.markdown(
    '<div class="scene-card">'
    f'<div class="scene-speaker">{html.escape(speaker)}</div>'
    f'<div class="scene-title">{html.escape(scene["title"])}</div>'
    f'<div class="scene-body">'
    f'{html.escape(scene["body"])}<br><br>'
    f'{html.escape(scene["extra_line"]).replace(chr(10), "<br>")}'
    "</div></div>",
    unsafe_allow_html=True,
)

for index, option in enumerate(options_for_scene(game)):
    label = option.get("label", option.get("option_label"))
    if st.button(
        label,
        key=f"choice_{game['turn']}_{index}",
        use_container_width=True,
    ):
        st.session_state.game = choose(game, option)
        st.rerun()

st.caption(
    "人物情緒會累積；當親近、懷疑、焦慮、好奇等情緒達到門檻，"
    "會直接解鎖新的 🎭 情緒選項。"
)
