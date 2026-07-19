from __future__ import annotations
import json, random
from .db import connect
TOTAL_TURNS=18
ACT_LABELS={1:'第一幕｜我只是來上班',2:'第二幕｜這公司真的有問題',3:'第三幕｜怪功開始改變劇情',4:'第四幕｜你要選哪一邊'}
def rows(sql,p=()):
    with connect() as c:return c.execute(sql,p).fetchall()
def row(sql,p=()):
    with connect() as c:return c.execute(sql,p).fetchone()
def act_for(t): return 1 if t<=3 else 2 if t<=8 else 3 if t<=13 else 4
def new_game(name='新人',seed=None):
    rg=random.Random(seed); cs=[dict(x) for x in rows('SELECT * FROM characters')]; core=[x for x in cs if x['is_core']]; sup=[x for x in cs if not x['is_core']]; active=core+rg.sample(sup,6); sec=dict(rg.choice(rows('SELECT * FROM world_secrets')))
    ids={}
    for c in active: ids[c['role_key']]=rg.choice(rows('SELECT variant_text FROM character_identity_variants WHERE role_key=?',(c['role_key'],)))['variant_text']
    s={'player_name':name.strip() or '新人','turn':0,'secret_key':sec['secret_key'],'secret_title':sec['title'],'secret_description':sec['description'],'active_roles':[c['role_key'] for c in active],'active_characters':{c['role_key']:c for c in active},'identities':ids,'relationships':{c['role_key']:0 for c in active},'techniques':[],'technique_use_count':{},'clues':[],'secret_progress':0,'flags':[],'used_event_ids':[],'used_families':[],'used_choice_texts':[],'recent_focus':[],'current_scene':None,'last_result':'','last_gain':'','dialogue_queue':[],'dialogue_pending':False,'used_dialogue_texts':[],'pending_fallouts':[],'ending_bias':'','ending':None,'rng_seed':rg.randrange(1,10**9)}
    ensure_scene(s); return s
def rng(s): s['rng_seed']=(s['rng_seed']*1103515245+12345)%(2**31); return random.Random(s['rng_seed'])
def resolve_focus(s,focus):
    if focus!='support': return focus
    opts=[x for x in s['active_roles'] if x not in ['guard','rookie','manager','hr','friend','ceo','finance','legal','it','general','courier','cafe']]
    return rng(s).choice(opts)
def pending_scene(s):
    due=[x for x in s['pending_fallouts'] if x['due_turn']<=s['turn']]
    if not due:return None
    x=due[0]; s['pending_fallouts'].remove(x)
    return {'id':-100000-s['turn'],'family':'fallout_'+x['tech_key'],'act':act_for(s['turn']),'category':'technique','focus_role':x['focus_role'],'title':f"《{x['tech_name']}》的後遺症回來了",'body':x['fallout_text'],'extra_line':'你前面用過的功法，現在開始真正改變別人的行動方式。','tags':['technique','social'],'is_special':True,'special_choices':[{'id':'a','label':f"承認《{x['tech_name']}》就是你用的，讓影響繼續",'action_kind':'technique','outcome_text':f"你沒有否認。從這一刻起，大家開始把《{x['tech_name']}》當成你的招牌。",'relationship_delta':1,'clue_gain':0,'learn_tag':'','learn_chance':0.0,'flag':'owned_'+x['tech_key'],'ending_bias':''},{'id':'b','label':'裝傻，堅稱那只是一次非常剛好的巧合','action_kind':'observe','outcome_text':'沒有人真的相信你，但至少大家暫時沒有繼續追問。','relationship_delta':0,'clue_gain':0,'learn_tag':'','learn_chance':0.0,'flag':'deny_'+x['tech_key'],'ending_bias':''}]}
def ensure_scene(s):
    if s.get('ending'):return {}
    if s.get('current_scene'):return s['current_scene']
    f=pending_scene(s)
    if f: s['current_scene']=f; return f
    a=act_for(s['turn'])
    if s['turn']==TOTAL_TURNS-1: rs=rows('SELECT * FROM events WHERE is_finale=1 AND secret_key=? ORDER BY RANDOM() LIMIT 30',(s['secret_key'],))
    elif s['turn']==0: rs=rows("SELECT * FROM events WHERE family='orientation_contract' ORDER BY RANDOM() LIMIT 20")
    else: rs=rows('SELECT * FROM events WHERE is_finale=0 AND act=? ORDER BY RANDOM() LIMIT 120',(a,))
    cand=[]
    for q in rs:
        d=dict(q)
        if d['id'] in s['used_event_ids'] or d['family'] in s['used_families']:continue
        fr=resolve_focus(s,d['focus_role'])
        if s['recent_focus'] and fr==s['recent_focus'][-1]:continue
        d['focus_role']=fr; cand.append(d)
    if not cand:
        for q in rs:
            d=dict(q)
            if d['id'] in s['used_event_ids'] or d['family'] in s['used_families']:continue
            d['focus_role']=resolve_focus(s,d['focus_role']); cand.append(d)
    if not cand: raise RuntimeError('找不到可用事件')
    sc=rng(s).choice(cand); sc['tags']=json.loads(sc['tags_json']); sc['is_special']=False; s['current_scene']=sc; s['used_event_ids'].append(sc['id']); s['used_families'].append(sc['family']); s['recent_focus']=(s['recent_focus']+[sc['focus_role']])[-3:]; return sc
def tech_option(s,sc):
    if not s['techniques']:return None
    poss=[]; tags=set(sc.get('tags',[]))
    for k in s['techniques']:
        t=row('SELECT * FROM techniques WHERE tech_key=?',(k,)); matches=tags&set(json.loads(t['trigger_tags_json']))
        for tag in matches:
            for q in rows('SELECT * FROM technique_uses WHERE tech_key=? AND scene_tag=? ORDER BY RANDOM() LIMIT 8',(k,tag)):
                d=dict(q)
                if d['option_label'] in s['used_choice_texts']:continue
                d.update({'is_technique':True,'action_kind':'technique','relationship_delta':1,'clue_gain':1 if 'secret' in tags else 0,'learn_tag':'','learn_chance':0.0,'flag':'used_'+k,'ending_bias':'','tech_name':t['name']}); poss.append(d)
    return rng(s).choice(poss) if poss else None
def options_for_scene(s):
    sc=ensure_scene(s)
    if sc.get('is_special'):return sc['special_choices']
    ch=[dict(x) for x in rows('SELECT * FROM choices WHERE event_id=? ORDER BY sort_order',(sc['id'],)) if x['label'] not in s['used_choice_texts']]
    to=tech_option(s,sc)
    if to:ch.append(to)
    return ch[:4]
def learn(s,tag,force=False):
    if not tag:return None
    cand=[]
    for q in rows('SELECT * FROM techniques'):
        d=dict(q)
        if d['tech_key'] in s['techniques']:continue
        if tag in json.loads(d['trigger_tags_json']):cand.append(d)
    if not cand:return None
    if not force and rng(s).random()>0.55:return None
    t=rng(s).choice(cand); s['techniques'].append(t['tech_key']); s['last_gain']=f"🥋 你在剛才的選擇中意外領悟了《{t['name']}》：{t['description']}"; return t
def reaction(s,role_,act,action):
    rs=rows('SELECT reaction_text FROM character_reactions WHERE role_key=? AND act=? AND action_kind=? ORDER BY RANDOM() LIMIT 30',(role_,act,action)) or rows('SELECT reaction_text FROM character_reactions WHERE role_key=? AND act=? ORDER BY RANDOM() LIMIT 30',(role_,act))
    return rng(s).choice(rs)['reaction_text'] if rs else ''
def ambient(s,act,cat,action):
    rs=rows('SELECT response_text FROM ambient_responses WHERE act=? AND category=? AND action_kind=? ORDER BY RANDOM() LIMIT 40',(act,cat,action)) or rows('SELECT response_text FROM ambient_responses WHERE act=? AND category=? ORDER BY RANDOM() LIMIT 40',(act,cat))
    return rng(s).choice(rs)['response_text'] if rs else ''
def clue(s):
    st=min(4,s['secret_progress']+1); q=row('SELECT clue_text FROM secret_clues WHERE secret_key=? AND stage=?',(s['secret_key'],st))
    if q and q['clue_text'] not in s['clues']:s['clues'].append(q['clue_text']); s['secret_progress']=st; return q['clue_text']
    return ''
def finish(s):
    bias=s.get('ending_bias') or 'absurd'; q=row('SELECT title,body FROM endings WHERE secret_key=? AND ending_bias=?',(s['secret_key'],bias)); s['ending']={'title':q['title'],'body':q['body'],'secret_title':s['secret_title']}

def _fresh_pick(s,items):
    if not items:return ''
    used=set(s.get('used_dialogue_texts',[]))
    fresh=[x for x in items if x not in used]
    pool=fresh or items
    pick=rng(s).choice(pool)
    s.setdefault('used_dialogue_texts',[]).append(pick)
    if len(s['used_dialogue_texts'])>120:s['used_dialogue_texts']=s['used_dialogue_texts'][-120:]
    return pick

def dialogue_for(s,role_,action,sc,opt):
    npc=s['active_characters'].get(role_,{}).get('short_name','？？？')
    label=opt.get('label',opt.get('option_label',''))
    out=[{'speaker':s.get('player_name','新人'),'text':'「'+label+'」','kind':'player'}]

    # Exact event context for database choices.
    hook=''
    choice_id=opt.get('id')
    if isinstance(choice_id,int) and not opt.get('is_technique'):
        meta=row('SELECT hook,consequence FROM choice_dialogue_meta WHERE choice_id=?',(choice_id,))
        if meta:
            hook=meta['hook']
            verbs={
                'probe':'追問','direct':'直接碰','observe':'盯著看',
                'public':'公開','reform':'改掉','conflict':'硬闖',
                'learn':'試著理解','technique':'拿功法處理'
            }
            verb=verbs.get(action,'處理')
            tmpls=[x['template_text'] for x in rows(
                'SELECT template_text FROM role_response_templates WHERE role_key=? ORDER BY RANDOM() LIMIT 20',
                (role_,)
            )]
            tmpl=_fresh_pick(s,tmpls)
            if tmpl:
                rendered=tmpl.format(verb=verb,hook=hook)
                out.append({'speaker':npc,'text':rendered,'kind':'npc'})
            out.append({'speaker':'旁白','text':meta['consequence'],'kind':'narration'})

    # Technique options get a role-specific comment about the exact technique.
    if opt.get('is_technique'):
        tech=opt.get('tech_name','這門怪功')
        tmpls=[x['template_text'] for x in rows(
            'SELECT template_text FROM technique_role_templates_v2 WHERE role_key=? ORDER BY RANDOM() LIMIT 20',
            (role_,)
        )]
        tmpl=_fresh_pick(s,tmpls)
        if tmpl:
            out.append({'speaker':npc,'text':tmpl.format(tech=tech),'kind':'npc'})

    # Special/fallout choices may not have a database choice id.
    if len(out)==1:
        specials=[
            '「你這個選法，會讓事情更麻煩。好消息是，也可能更有趣。」',
            '「我本來以為你會選安全的那條。看來我還不夠了解你。」',
            '「好。既然你決定這樣做，我就當今天沒有正常下班這回事。」',
            '「這不是我最推薦的答案，但確實是最像你的答案。」'
        ]
        out.append({'speaker':npc,'text':_fresh_pick(s,specials),'kind':'npc'})

    # One extra line in the character's own voice, fresh within the run.
    if len(out)<4:
        voice=[x['voice_line'] for x in rows(
            'SELECT voice_line FROM role_voice_lines_v2 WHERE role_key=? ORDER BY RANDOM() LIMIT 30',
            (role_,)
        )]
        v=_fresh_pick(s,voice)
        if v:out.append({'speaker':npc,'text':v,'kind':'npc'})

    return out[:4]

def choose(s,opt):
    sc=ensure_scene(s); role_=sc['focus_role']; action=opt.get('action_kind','observe'); s['last_gain']=''; label=opt.get('label',opt.get('option_label')); s['dialogue_queue']=dialogue_for(s,role_,action,sc,opt); s['dialogue_pending']=True; s['used_choice_texts'].append(label); s['relationships'][role_]=s['relationships'].get(role_,0)+int(opt.get('relationship_delta',0)); flag=opt.get('flag','');
    if flag and flag not in s['flags']:s['flags'].append(flag)
    cl='';
    if int(opt.get('clue_gain',0))>0:cl=clue(s)
    if opt.get('is_technique'):
        k=opt['tech_key']; s['technique_use_count'][k]=s['technique_use_count'].get(k,0)+1; due=s['turn']+rng(s).randint(2,4)
        if due<TOTAL_TURNS-1:s['pending_fallouts'].append({'due_turn':due,'tech_key':k,'tech_name':opt['tech_name'],'fallout_text':opt['fallout_text'],'focus_role':role_})
    else:
        force=s['turn']>=2 and not s['techniques'];
        if force or rng(s).random()<float(opt.get('learn_chance',0)):learn(s,opt.get('learn_tag',''),force=force)
    parts=[opt['outcome_text']]
    if cl:parts.append('🔎 新線索：'+cl)
    s['last_result']='\n\n'.join(x for x in parts if x); eb=opt.get('ending_bias','');
    if eb:s['ending_bias']=eb
    s['turn']+=1; s['current_scene']=None
    if s['turn']>=TOTAL_TURNS:finish(s)
    else:ensure_scene(s)
    return s
def relationship_label(v):
    return '明顯站在你這邊' if v>=4 else '開始信任你' if v>=2 else '對你非常戒備' if v<=-3 else '有點不爽你' if v<=-1 else '還在觀察你'
def active_character_cards(s):
    return [{'name':s['active_characters'][r]['short_name'],'job':s['active_characters'][r]['job'],'relationship':relationship_label(s['relationships'].get(r,0)),'hook':s['active_characters'][r]['comic_hook']} for r in s['active_roles']]
def owned_techniques(s):
    if not s['techniques']:return []
    ph=','.join('?' for _ in s['techniques']); return [dict(x) for x in rows(f'SELECT * FROM techniques WHERE tech_key IN ({ph})',tuple(s['techniques']))]
