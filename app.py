import html
import time
import streamlit as st
from game.engine import ACT_LABELS,TOTAL_TURNS,active_character_cards,choose,ensure_scene,new_game,options_for_scene,owned_techniques
st.set_page_config(page_title='都市武俠：我的公司好像是邪教',page_icon='🥋',layout='centered',initial_sidebar_state='collapsed')
st.markdown("""<style>[data-testid='stAppViewContainer']{background:#0f1115;color:#eef1f5}[data-testid='stMainBlockContainer']{max-width:520px;padding-top:.6rem;padding-bottom:1rem}header,footer{visibility:hidden;height:0}.title{font-size:1.18rem;font-weight:800}.muted{color:#a8adb8;font-size:.88rem}.card{border:1px solid #30343b;border-radius:16px;padding:1rem;background:#171a20;margin:.55rem 0}.body{line-height:1.78;white-space:pre-wrap;color:#f2f4f8}.result{border-left:3px solid #9ca8b8;padding:.7rem .85rem;margin:.45rem 0;background:#171a20;border-radius:10px;line-height:1.7;white-space:pre-wrap;color:#eef1f5}.gain{border:1px solid #665c2d;padding:.65rem .8rem;margin:.45rem 0;border-radius:10px;background:#1d1a10}div.stButton>button{width:100%;min-height:3.15rem;border-radius:12px;text-align:left;justify-content:flex-start;white-space:normal;line-height:1.35}div[data-testid='stPopover'] button{min-height:2.1rem;text-align:center;justify-content:center}</style>

st.markdown(r'''
<style>
/* ===== V4.3 古風武俠介面 ===== */
:root{
    --ink:#15110d;
    --ink-2:#1c1611;
    --panel:#241b14;
    --panel-2:#2d2117;
    --paper:#f4e8c9;
    --paper-soft:#dfcfaa;
    --muted:#b9a985;
    --bronze:#b58a4a;
    --bronze-2:#8f6938;
    --vermilion:#8f2f26;
    --vermilion-2:#6f221c;
    --line:#6f5636;
}

/* App background and all default text */
[data-testid="stAppViewContainer"]{
    background:
        radial-gradient(circle at 20% 0%, rgba(181,138,74,.07), transparent 30%),
        linear-gradient(180deg,#15110d 0%,#19130f 55%,#120f0c 100%) !important;
    color:var(--paper) !important;
}
[data-testid="stMainBlockContainer"]{
    max-width:520px !important;
    padding-top:.7rem !important;
    padding-bottom:1rem !important;
}
header,footer{visibility:hidden;height:0}

/* Typography */
html,body,[class*="css"],.stMarkdown,p,li,label,span,div{
    font-family:"Noto Serif TC","Songti TC","PMingLiU","MingLiU",serif;
}
.stMarkdown p,
.stMarkdown li,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li{
    color:var(--paper) !important;
}
.game-title{
    color:#fff3d2 !important;
    font-size:1.18rem;
    font-weight:800;
    letter-spacing:.04em;
    text-shadow:0 1px 0 #000;
}
.muted{
    color:var(--muted) !important;
    font-size:.88rem;
}

/* Scene / result / gain cards */
.scene-card{
    border:1px solid var(--bronze-2) !important;
    border-radius:14px !important;
    padding:1rem !important;
    background:
        linear-gradient(180deg,rgba(45,33,23,.98),rgba(31,24,18,.98)) !important;
    box-shadow:
        inset 0 0 0 1px rgba(244,232,201,.035),
        0 8px 24px rgba(0,0,0,.25);
}
.scene-title{
    color:#fff0c8 !important;
    font-size:1.12rem !important;
    font-weight:800 !important;
    margin-bottom:.65rem !important;
}
.body,.scene-body{
    color:#f7edda !important;
    line-height:1.8 !important;
    font-size:1rem !important;
    white-space:pre-wrap !important;
}
.speaker{
    color:#d9bd82 !important;
    font-size:.86rem !important;
    margin-bottom:.4rem !important;
}
.result,.result-card{
    border-left:4px solid var(--bronze) !important;
    border-top:1px solid #4e3c28 !important;
    border-right:1px solid #4e3c28 !important;
    border-bottom:1px solid #4e3c28 !important;
    padding:.75rem .9rem !important;
    margin:.45rem 0 .65rem 0 !important;
    background:#201812 !important;
    border-radius:10px !important;
    line-height:1.72 !important;
    white-space:pre-wrap !important;
    color:#f5ead3 !important;
}
.gain-card{
    border:1px solid #9b7a41 !important;
    background:#292012 !important;
    color:#ffe8a6 !important;
    border-radius:10px !important;
    padding:.7rem .85rem !important;
}

/* Main choice buttons */
div.stButton > button,
button[kind="secondary"],
button[kind="primary"]{
    width:100% !important;
    min-height:3.15rem !important;
    border-radius:11px !important;
    text-align:left !important;
    justify-content:flex-start !important;
    white-space:normal !important;
    line-height:1.42 !important;
    background:linear-gradient(180deg,#2d2117,#211811) !important;
    color:#fff0cf !important;
    border:1px solid #8d6a3a !important;
    box-shadow:inset 0 0 0 1px rgba(255,240,207,.025) !important;
}
div.stButton > button p,
div.stButton > button span,
button[kind="secondary"] p,
button[kind="secondary"] span,
button[kind="primary"] p,
button[kind="primary"] span{
    color:#fff0cf !important;
}
div.stButton > button:hover,
button[kind="secondary"]:hover,
button[kind="primary"]:hover{
    background:linear-gradient(180deg,#3a2a1c,#2a1d14) !important;
    border-color:#d0a55e !important;
    color:#fff8e7 !important;
}
div.stButton > button:focus,
button[kind="secondary"]:focus,
button[kind="primary"]:focus{
    box-shadow:0 0 0 2px rgba(181,138,74,.35) !important;
}

/* Popover trigger buttons: 人物 / 功法 / 線索 */
div[data-testid="stPopover"] > div > button,
[data-testid="stPopover"] button{
    background:#2a2017 !important;
    color:#f6e7c4 !important;
    border:1px solid #83643a !important;
    min-height:2.35rem !important;
    border-radius:10px !important;
}
div[data-testid="stPopover"] button p,
div[data-testid="stPopover"] button span{
    color:#f6e7c4 !important;
}

/* BaseWeb popover surface: force dark parchment */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
[data-baseweb="popover"] [role="dialog"],
[data-testid="stPopoverBody"],
[data-testid="stPopoverBody"] > div{
    background:#241b14 !important;
    color:#f5e7c6 !important;
    border-color:#8b6a3e !important;
}
div[data-baseweb="popover"] *,
[data-testid="stPopoverBody"] *,
[data-testid="stPopoverBody"] p,
[data-testid="stPopoverBody"] span,
[data-testid="stPopoverBody"] div,
[data-testid="stPopoverBody"] li,
[data-testid="stPopoverBody"] strong{
    color:#f5e7c6 !important;
}

/* Generic dialogs / floating surfaces that Streamlit may use */
[role="dialog"]{
    background:#241b14 !important;
    color:#f5e7c6 !important;
    border:1px solid #8b6a3e !important;
}
[role="dialog"] *{
    color:#f5e7c6 !important;
}

/* Inputs */
input,
textarea,
[data-baseweb="input"] > div{
    background:#211811 !important;
    color:#f7ebd2 !important;
    border-color:#765936 !important;
}
input::placeholder,textarea::placeholder{
    color:#a89570 !important;
}

/* Progress bar */
[data-testid="stProgress"] > div > div{
    background:#2a2017 !important;
}
[data-testid="stProgress"] > div > div > div{
    background:linear-gradient(90deg,#7c2d24,#b58a4a) !important;
}

/* Dividers / captions */
hr{
    border-color:#4e3b27 !important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] *{
    color:#aa9a79 !important;
}

/* Expander fallback */
[data-testid="stExpander"]{
    background:#211811 !important;
    border:1px solid #665035 !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary *{
    color:#f2dfb9 !important;
}

/* Scrollbar */
::-webkit-scrollbar{width:8px}
::-webkit-scrollbar-track{background:#15110d}
::-webkit-scrollbar-thumb{background:#6f5636;border-radius:8px}
::-webkit-scrollbar-thumb:hover{background:#8f6938}
</style>
''', unsafe_allow_html=True)
""",unsafe_allow_html=True)

st.markdown(r"""
<style>
.dialogue-stage{
    border:1px solid #8d6a3a;
    border-left:4px solid #8f2f26;
    background:linear-gradient(180deg,#211912,#17110d);
    border-radius:12px;
    padding:.8rem .9rem;
    margin:.55rem 0 .8rem 0;
    box-shadow:0 6px 18px rgba(0,0,0,.22);
}
.dialogue-line{
    padding:.42rem 0 .5rem 0;
    border-bottom:1px solid rgba(181,138,74,.18);
}
.dialogue-line:last-child{border-bottom:none}
.dialogue-speaker{
    color:#d8ab5d !important;
    font-size:.8rem;
    font-weight:800;
    letter-spacing:.07em;
    margin-bottom:.2rem;
}
.dialogue-text{
    color:#fff3d6 !important;
    font-size:1.02rem;
    line-height:1.65;
    font-weight:600;
}
.dialogue-player .dialogue-speaker{color:#c9b88e !important}
.dialogue-player .dialogue-text{color:#e9ddc2 !important}
</style>
""", unsafe_allow_html=True)


if 'game' not in st.session_state:
    st.markdown('<div class="title">🥋 都市武俠：我的公司好像是邪教</div>',unsafe_allow_html=True); st.markdown('<div class="muted">手機短篇互動小說｜18 個主要決策｜約 20～30 分鐘</div>',unsafe_allow_html=True); st.markdown('---'); st.write('你只是來報到的新人。直到你發現 HR 的員工守則提到門規、保全好像會輕功、地下室有人午休比武。更糟的是，你開始在普通對話裡莫名其妙學會奇怪武功。'); name=st.text_input('你的名字',value='新人',max_chars=12)
    if st.button('開始第一天報到',type='primary',use_container_width=True):st.session_state.game=new_game(name);st.rerun()
    st.stop()

g=st.session_state.game

# 玩家選擇後，先逐句播放對話字幕。
if g.get('dialogue_pending') and g.get('dialogue_queue'):
    box=st.empty()
    shown=[]
    for ln in g['dialogue_queue']:
        shown.append(ln)
        blocks=[]
        for x in shown:
            cls='dialogue-line dialogue-player' if x.get('kind')=='player' else 'dialogue-line'
            blocks.append(
                '<div class="'+cls+'">'
                '<div class="dialogue-speaker">'+html.escape(str(x.get('speaker','')))+'</div>'
                '<div class="dialogue-text">'+html.escape(str(x.get('text','')))+'</div>'
                '</div>'
            )
        box.markdown('<div class="dialogue-stage">'+''.join(blocks)+'</div>',unsafe_allow_html=True)
        time.sleep(0.62 if ln.get('kind')=='player' else 0.9)
    g['dialogue_pending']=False
    st.session_state.game=g

if g.get('ending'):
    e=g['ending']; st.markdown('<div class="title">🏁 本局結束</div>',unsafe_allow_html=True); st.markdown(f'<div class="card"><b>{html.escape(e["title"])}</b><div class="body">{html.escape(e["body"])}</div></div>',unsafe_allow_html=True); st.write('**你最後揭開的核心秘密：** '+e['secret_title']); st.write(f"**本局學會功法：** {len(g['techniques'])} 門　　**找到線索：** {len(g['clues'])} 條")
    if st.button('重新報到，開始另一條世界線',type='primary',use_container_width=True):del st.session_state.game;st.rerun()
    st.stop()
sc=ensure_scene(g); st.markdown('<div class="title">🥋 都市武俠：我的公司好像是邪教</div>',unsafe_allow_html=True); st.markdown(f'<div class="muted">{ACT_LABELS[sc["act"]]}　｜　第 {min(g["turn"]+1,TOTAL_TURNS)}/{TOTAL_TURNS} 個決定</div>',unsafe_allow_html=True); st.progress(g['turn']/TOTAL_TURNS)
c1,c2,c3=st.columns(3)
with c1:
    with st.popover('👥 人物',use_container_width=True):
        for x in active_character_cards(g):st.markdown(f"**{x['name']}｜{x['job']}**  \n{x['relationship']}  \n{x['hook']}")
with c2:
    with st.popover('🥋 功法',use_container_width=True):
        ts=owned_techniques(g)
        if not ts:st.caption('還沒有功法。它們會從某些對話選項與事件中突然出現。')
        for t in ts:st.markdown(f"**《{t['name']}》**  \n{t['description']}")
with c3:
    with st.popover('🔎 線索',use_container_width=True):
        if not g['clues']:st.caption('目前只有一種感覺：這公司真的不太正常。')
        for x in g['clues'][-6:]:st.markdown('• '+x)
if g.get('last_gain'):st.markdown('<div class="gain">'+html.escape(g['last_gain'])+'</div>',unsafe_allow_html=True)
if g.get('last_result'):st.markdown('<div class="result"><b>剛才發生</b><br>'+html.escape(g['last_result']).replace('\n','<br>')+'</div>',unsafe_allow_html=True)
f=g['active_characters'].get(sc['focus_role']); speaker=f"{f['short_name']}｜{f['job']}" if f else '公司內部'; st.markdown(f'<div class="card"><div class="muted">{html.escape(speaker)}</div><b>{html.escape(sc["title"])}</b><div class="body">{html.escape(sc["body"])}\n\n{html.escape(sc["extra_line"])}</div></div>',unsafe_allow_html=True)
for i,o in enumerate(options_for_scene(g)):
    label=o.get('label',o.get('option_label'))
    if st.button(label,key=f"c_{g['turn']}_{i}",use_container_width=True):st.session_state.game=choose(g,o);st.rerun()
st.caption('每局事件家族不重複；已學會功法會依場景重新出現在後續選項中。')
