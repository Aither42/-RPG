import html
import streamlit as st
from game.engine import ACT_LABELS,TOTAL_TURNS,active_character_cards,choose,ensure_scene,new_game,options_for_scene,owned_techniques
st.set_page_config(page_title='都市武俠：我的公司好像是邪教',page_icon='🥋',layout='centered',initial_sidebar_state='collapsed')
st.markdown("""<style>[data-testid='stAppViewContainer']{background:#0f1115;color:#eef1f5}[data-testid='stMainBlockContainer']{max-width:520px;padding-top:.6rem;padding-bottom:1rem}header,footer{visibility:hidden;height:0}.title{font-size:1.18rem;font-weight:800}.muted{color:#a8adb8;font-size:.88rem}.card{border:1px solid #30343b;border-radius:16px;padding:1rem;background:#171a20;margin:.55rem 0}.body{line-height:1.78;white-space:pre-wrap;color:#f2f4f8}.result{border-left:3px solid #9ca8b8;padding:.7rem .85rem;margin:.45rem 0;background:#171a20;border-radius:10px;line-height:1.7;white-space:pre-wrap;color:#eef1f5}.gain{border:1px solid #665c2d;padding:.65rem .8rem;margin:.45rem 0;border-radius:10px;background:#1d1a10}div.stButton>button{width:100%;min-height:3.15rem;border-radius:12px;text-align:left;justify-content:flex-start;white-space:normal;line-height:1.35}div[data-testid='stPopover'] button{min-height:2.1rem;text-align:center;justify-content:center}</style>""",unsafe_allow_html=True)
if 'game' not in st.session_state:
    st.markdown('<div class="title">🥋 都市武俠：我的公司好像是邪教</div>',unsafe_allow_html=True); st.markdown('<div class="muted">手機短篇互動小說｜18 個主要決策｜約 20～30 分鐘</div>',unsafe_allow_html=True); st.markdown('---'); st.write('你只是來報到的新人。直到你發現 HR 的員工守則提到門規、保全好像會輕功、地下室有人午休比武。更糟的是，你開始在普通對話裡莫名其妙學會奇怪武功。'); name=st.text_input('你的名字',value='新人',max_chars=12)
    if st.button('開始第一天報到',type='primary',use_container_width=True):st.session_state.game=new_game(name);st.rerun()
    st.stop()
g=st.session_state.game
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
