
from __future__ import annotations
import json, random
from .db import connect

TOTAL_TURNS=15
ACT_LABELS={1:"第一幕｜我只是來上班",2:"第二幕｜這公司真的有問題",3:"第三幕｜怪功開始改變劇情",4:"第四幕｜你要選哪一邊"}

def rows(sql,p=()):
    with connect() as c:return c.execute(sql,p).fetchall()
def row(sql,p=()):
    with connect() as c:return c.execute(sql,p).fetchone()
def act_for(t): return 1 if t<=3 else 2 if t<=7 else 3 if t<=11 else 4
def rng(s):
    s["rng_seed"]=(s["rng_seed"]*1103515245+12345)%(2**31)
    return random.Random(s["rng_seed"])

def new_game(name="新人",seed=None):
    rg=random.Random(seed)
    cs=[dict(x) for x in rows("SELECT * FROM characters")]
    core=[x for x in cs if x["is_core"]]; sup=[x for x in cs if not x["is_core"]]
    active=core+rg.sample(sup,6); sec=dict(rg.choice(rows("SELECT * FROM world_secrets")))
    ids={}
    for ch in active:
        ids[ch["role_key"]]=rg.choice(rows("SELECT variant_text FROM character_identity_variants WHERE role_key=?",(ch["role_key"],)))["variant_text"]
    s={"player_name":name.strip() or "新人","turn":0,"secret_key":sec["secret_key"],"secret_title":sec["title"],"secret_description":sec["description"],
       "active_roles":[x["role_key"] for x in active],"active_characters":{x["role_key"]:x for x in active},"identities":ids,
       "relationships":{x["role_key"]:0 for x in active},"techniques":[],"technique_use_count":{},"active_technique_effects":[],
       "pending_technique_events":[],"technique_countered":[],"used_combos":[],"ending_votes":{"reform":0,"expose":0,"escape":0,"takeover":0,"absurd":0,"join":0},
       "clues":[],"secret_progress":0,"flags":[],"used_event_ids":[],"used_families":[],"used_choice_texts":[],
       "used_dialogue_texts":[],"used_dialogue_variant_ids":[],"recent_focus":[],"current_scene":None,"last_result":"","last_gain":"",
       "dialogue_queue":[],"dialogue_pending":False,"ending_bias":"","ending":None,"rng_seed":rg.randrange(1,10**9)}
    ensure_scene(s); return s

def resolve_focus(s,f):
    if f!="support":return f
    core={"guard","rookie","manager","hr","friend","ceo","finance","legal","it","general","courier","cafe"}
    return rng(s).choice([x for x in s["active_roles"] if x not in core])

def fresh(s,items):
    if not items:return ""
    used=set(s["used_dialogue_texts"]); pool=[x for x in items if x not in used] or items
    x=rng(s).choice(pool); s["used_dialogue_texts"].append(x); s["used_dialogue_texts"]=s["used_dialogue_texts"][-180:]; return x

def profile(k): return row("SELECT * FROM technique_effect_profiles_v3 WHERE tech_key=?",(k,))
def tech_name(k):
    q=row("SELECT name FROM techniques WHERE tech_key=?",(k,)); return q["name"] if q else k

def pending_scene(s):
    due=[x for x in s["pending_technique_events"] if x["due_turn"]<=s["turn"]]
    if not due:return None
    x=sorted(due,key=lambda z:z["due_turn"])[0]; s["pending_technique_events"].remove(x)
    role=x.get("focus_role") or rng(s).choice(s["active_roles"]); tn=x.get("tech_name","某門怪功")
    return {"id":-500000-s["turn"],"family":x["family"],"act":act_for(s["turn"]),"category":"technique","focus_role":role,
      "title":x["title"],"body":x["body"],"extra_line":f"這不是旁白提示，而是《{tn}》真的在後續世界留下痕跡。",
      "tags":["technique","social","secret"],"is_special":True,"special_choices":[
      {"id":"tc0","label":f"承認這是《{tn}》造成的，乾脆把後果也算自己頭上","action_kind":"technique","outcome_text":f"你承認《{tn}》就是你用的，從此大家不再把它當都市傳說。","relationship_delta":1,"clue_gain":0,"learn_tag":"","learn_chance":0.0,"flag":"owned_consequence","ending_bias":x.get("ending_bias","")},
      {"id":"tc1","label":f"找人研究怎麼破解《{tn}》，避免下次連自己也被反噬","action_kind":"reform","outcome_text":f"你開始替《{tn}》建立使用規則，至少比公司偷偷替你建立規則好。","relationship_delta":0,"clue_gain":0,"learn_tag":"","learn_chance":0.0,"flag":"counter_research","ending_bias":"reform"},
      {"id":"tc2","label":f"趁大家還在怕《{tn}》，把混亂拿去逼出更多真相","action_kind":"probe","outcome_text":f"你把《{tn}》造成的混亂當掩護，真的又挖到一些不該知道的東西。","relationship_delta":0,"clue_gain":1,"learn_tag":"","learn_chance":0.0,"flag":"weaponized_consequence","ending_bias":"expose"}]}

def add_ripple(s,sc):
    s["active_technique_effects"]=[x for x in s["active_technique_effects"] if x["expires_turn"]>=s["turn"]]
    if not s["active_technique_effects"]:return
    x=rng(s).choice(s["active_technique_effects"]); p=profile(x["tech_key"])
    if not p:return
    text=p["persistent_effect"]
    if s["technique_use_count"].get(x["tech_key"],0)>=2:text+=" "+p["countermeasure"]
    sc["extra_line"]=sc.get("extra_line","")+f"\n\n【功法餘波｜《{x['tech_name']}》】{text}"

def ensure_scene(s):
    if s.get("ending"):return {}
    if s.get("current_scene"):return s["current_scene"]
    ps=pending_scene(s)
    if ps:s["current_scene"]=ps; return ps
    a=act_for(s["turn"])
    if s["turn"]==TOTAL_TURNS-1: src=rows("SELECT * FROM events WHERE is_finale=1 AND secret_key=? ORDER BY RANDOM() LIMIT 40",(s["secret_key"],))
    elif s["turn"]==0: src=rows("SELECT * FROM events WHERE family='orientation_contract' ORDER BY RANDOM() LIMIT 20")
    else: src=rows("SELECT * FROM events WHERE is_finale=0 AND act=? ORDER BY RANDOM() LIMIT 160",(a,))
    cand=[]
    for q in src:
        d=dict(q)
        if d["id"] in s["used_event_ids"] or d["family"] in s["used_families"]:continue
        f=resolve_focus(s,d["focus_role"])
        if s["recent_focus"] and f==s["recent_focus"][-1]:continue
        d["focus_role"]=f; cand.append(d)
    if not cand:
        for q in src:
            d=dict(q)
            if d["id"] in s["used_event_ids"] or d["family"] in s["used_families"]:continue
            d["focus_role"]=resolve_focus(s,d["focus_role"]); cand.append(d)
    if not cand:raise RuntimeError("找不到可用事件")
    sc=rng(s).choice(cand); sc["tags"]=json.loads(sc["tags_json"]); sc["is_special"]=False; add_ripple(s,sc)
    s["current_scene"]=sc; s["used_event_ids"].append(sc["id"]); s["used_families"].append(sc["family"]); s["recent_focus"]=(s["recent_focus"]+[sc["focus_role"]])[-3:]; return sc

def tech_options(s,sc):
    poss=[]; tags=set(sc.get("tags",[]))
    for k in s["techniques"]:
        t=row("SELECT * FROM techniques WHERE tech_key=?",(k,))
        if not t:continue
        for tag in tags&set(json.loads(t["trigger_tags_json"])):
            for q in rows("SELECT * FROM technique_uses WHERE tech_key=? AND scene_tag=? ORDER BY RANDOM() LIMIT 8",(k,tag)):
                d=dict(q)
                if d["option_label"] in s["used_choice_texts"]:continue
                d.update({"is_technique":True,"action_kind":"technique","relationship_delta":1,"clue_gain":0,"learn_tag":"","learn_chance":0.0,
                          "flag":"used_"+k,"ending_bias":"","tech_name":t["name"],"scene_tag":tag})
                poss.append(d)
    return poss

def combo_option(s):
    owned=set(s["techniques"]); cand=[]
    for q in rows("SELECT * FROM technique_combo_effects_v3"):
        d=dict(q)
        if d["combo_key"] not in s["used_combos"] and d["tech_a"] in owned and d["tech_b"] in owned:cand.append(d)
    if not cand:return None
    x=rng(s).choice(cand)
    return {"id":"combo_"+x["combo_key"],"label":x["option_label"],"option_label":x["option_label"],"action_kind":"technique",
      "outcome_text":x["immediate_effect"],"relationship_delta":2,"clue_gain":0,"learn_tag":"","learn_chance":0.0,"flag":"combo_"+x["combo_key"],
      "ending_bias":x["ending_bias"],"is_combo":True,"combo_key":x["combo_key"],"combo_name":x["combo_name"],
      "delayed_title":x["delayed_title"],"delayed_body":x["delayed_body"]}

def options_for_scene(s):
    sc=ensure_scene(s)
    if sc.get("is_special"):return sc["special_choices"]
    ch=[dict(x) for x in rows("SELECT * FROM choices WHERE event_id=? ORDER BY sort_order",(sc["id"],)) if x["label"] not in s["used_choice_texts"]]
    combo=combo_option(s); ts=tech_options(s,sc); special=None
    if combo and rng(s).random()<0.45:special=combo
    elif ts:
        m=min(s["technique_use_count"].get(x["tech_key"],0) for x in ts); low=[x for x in ts if s["technique_use_count"].get(x["tech_key"],0)==m]; special=rng(s).choice(low)
    elif combo:special=combo
    if special:ch.append(special)
    return ch[:4]

def learn(s,tag,force=False):
    if not tag:return None
    cand=[]
    for q in rows("SELECT * FROM techniques"):
        d=dict(q)
        if d["tech_key"] not in s["techniques"] and tag in json.loads(d["trigger_tags_json"]):cand.append(d)
    if not cand or (not force and rng(s).random()>0.65):return None
    t=rng(s).choice(cand); s["techniques"].append(t["tech_key"]); p=profile(t["tech_key"])
    s["last_gain"]=f"🥋 你意外領悟《{t['name']}》：{t['description']} 這門功法屬於「{p['effect_type'] if p else '奇葩'}」型，之後不只會多一個選項。"; return t

def get_clue(s):
    st=min(4,s["secret_progress"]+1); q=row("SELECT clue_text FROM secret_clues WHERE secret_key=? AND stage=?",(s["secret_key"],st))
    if q and q["clue_text"] not in s["clues"]:s["clues"].append(q["clue_text"]); s["secret_progress"]=st; return q["clue_text"]
    return ""

def dialogue_variant(s,cid):
    vs=[dict(x) for x in rows("SELECT * FROM choice_dialogue_variants_v3 WHERE choice_id=?",(cid,))]
    pool=[x for x in vs if x["id"] not in s["used_dialogue_variant_ids"]] or vs
    if not pool:return None
    x=rng(s).choice(pool); s["used_dialogue_variant_ids"].append(x["id"]); return x

def dialogue_for(s,role,action,sc,opt):
    npc=s["active_characters"].get(role,{}).get("short_name","？？？"); label=opt.get("label",opt.get("option_label",""))
    out=[{"speaker":s["player_name"],"text":"「"+label+"」","kind":"player"}]
    if opt.get("is_combo"):
        out.append({"speaker":npc,"text":f"「你一次把兩門怪功疊在一起？……《{opt['combo_name']}》這名字誰取的？」","kind":"npc"})
    elif opt.get("is_technique"):
        rs=[x["reaction_text"] for x in rows("SELECT reaction_text FROM technique_role_reactions_v3 WHERE tech_key=? AND role_key=? ORDER BY RANDOM() LIMIT 10",(opt["tech_key"],role))]
        r=fresh(s,rs)
        if r:out.append({"speaker":npc,"text":"「"+r+"」" if not r.startswith("「") else r,"kind":"npc"})
        if s["technique_use_count"].get(opt["tech_key"],0)>=1:
            out.append({"speaker":npc,"text":"「而且你不是第一次用了。現在大家已經開始研究怎麼破解。」","kind":"npc"})
    else:
        cid=opt.get("id")
        if isinstance(cid,int):
            v=dialogue_variant(s,cid)
            if v:
                verb={"probe":"追問","direct":"直接碰","observe":"盯著看","public":"公開","reform":"改掉","conflict":"硬闖"}.get(action,"處理")
                ts=[x["template_text"] for x in rows("SELECT template_text FROM role_response_templates_v3 WHERE role_key=? ORDER BY RANDOM() LIMIT 40",(role,))]
                t=fresh(s,ts)
                if t:out.append({"speaker":npc,"text":t.format(verb=verb,hook=v["hook"]),"kind":"npc"})
                out.append({"speaker":"旁白","text":v["consequence"],"kind":"narration"})
    if len(out)<4:
        vs=[x["voice_line"] for x in rows("SELECT voice_line FROM role_voice_lines_v3 WHERE role_key=? ORDER BY RANDOM() LIMIT 50",(role,))]
        v=fresh(s,vs)
        if v:out.append({"speaker":npc,"text":v,"kind":"npc"})
    if len(out)==1:out.append({"speaker":npc,"text":"「你這個選法不一定安全，但至少不會無聊。」","kind":"npc"})
    return out[:4]

def schedule_effect(s,k,n,role):
    p=profile(k)
    if not p:return
    s["active_technique_effects"].append({"tech_key":k,"tech_name":n,"expires_turn":s["turn"]+int(p["duration_turns"])})
    fs=rows("SELECT title,body FROM technique_effect_followups_v3 WHERE tech_key=? ORDER BY RANDOM() LIMIT 3",(k,))
    if fs:
        x=rng(s).choice(fs); due=min(TOTAL_TURNS-2,s["turn"]+rng(s).randint(1,3))
        if due>s["turn"]:s["pending_technique_events"].append({"due_turn":due,"tech_key":k,"tech_name":n,"focus_role":role,"title":x["title"],"body":x["body"],"ending_bias":p["ending_bias"],"family":"tech_consequence_"+k})
    s["ending_votes"][p["ending_bias"]]=s["ending_votes"].get(p["ending_bias"],0)+1

def apply_tech(s,sc,opt):
    k=opt["tech_key"]; n=opt["tech_name"]; p=profile(k); old=s["technique_use_count"].get(k,0); s["technique_use_count"][k]=old+1; out=[]
    if p:
        out.append("🥋 功法實際影響："+p["immediate_effect"])
        if int(p["clue_bonus"])>0 and sc["category"]!="finale":
            cl=get_clue(s)
            if cl:out.append("🔎 《"+n+"》額外逼出的線索："+cl)
        if old>=1:
            out.append("⚠️ 對手已開始反制："+p["countermeasure"])
            if k not in s["technique_countered"]:s["technique_countered"].append(k)
        schedule_effect(s,k,n,sc["focus_role"])
    return out

def apply_combo(s,sc,opt):
    if opt["combo_key"] not in s["used_combos"]:s["used_combos"].append(opt["combo_key"])
    s["ending_votes"][opt["ending_bias"]]=s["ending_votes"].get(opt["ending_bias"],0)+2
    due=min(TOTAL_TURNS-2,s["turn"]+2)
    if due>s["turn"]:s["pending_technique_events"].append({"due_turn":due,"tech_key":opt["combo_key"],"tech_name":opt["combo_name"],"focus_role":sc["focus_role"],"title":opt["delayed_title"],"body":opt["delayed_body"],"ending_bias":opt["ending_bias"],"family":"combo_consequence_"+opt["combo_key"]})
    return ["🔥 組合技成立："+opt["combo_name"],opt["outcome_text"],"這個組合已被世界記住，之後會有專屬後果。"]

def choose(s,opt):
    sc=ensure_scene(s); role=sc["focus_role"]; action=opt.get("action_kind","observe"); label=opt.get("label",opt.get("option_label",""))
    s["last_gain"]=""; s["dialogue_queue"]=dialogue_for(s,role,action,sc,opt); s["dialogue_pending"]=True
    s["used_choice_texts"].append(label); s["used_choice_texts"]=s["used_choice_texts"][-250:]
    if role in s["relationships"]:s["relationships"][role]+=int(opt.get("relationship_delta",0))
    flag=opt.get("flag","")
    if flag and flag not in s["flags"]:s["flags"].append(flag)
    parts=[]
    if opt.get("is_combo"):parts+=apply_combo(s,sc,opt)
    elif opt.get("is_technique"):parts.append(opt["outcome_text"]); parts+=apply_tech(s,sc,opt)
    else:parts.append(opt["outcome_text"])
    if int(opt.get("clue_gain",0))>0:
        cl=get_clue(s)
        if cl:parts.append("🔎 新線索："+cl)
    if not opt.get("is_technique") and not opt.get("is_combo"):
        force=s["turn"]>=2 and not s["techniques"]
        if force or rng(s).random()<float(opt.get("learn_chance",0)):learn(s,opt.get("learn_tag",""),force)
    eb=opt.get("ending_bias","")
    if eb:s["ending_bias"]=eb; s["ending_votes"][eb]=s["ending_votes"].get(eb,0)+1
    s["last_result"]="\n\n".join(x for x in parts if x); s["turn"]+=1; s["current_scene"]=None
    if s["turn"]>=TOTAL_TURNS:finish(s)
    else:ensure_scene(s)
    return s

def finish(s):
    selected=s.get("ending_bias") or "absurd"
    if s["ending_votes"]:
        b,score=max(s["ending_votes"].items(),key=lambda x:x[1])
        if score>=2:selected=b
    q=row("SELECT title,body FROM endings WHERE secret_key=? AND ending_bias=?",(s["secret_key"],selected)) or row("SELECT title,body FROM endings WHERE secret_key=? LIMIT 1",(s["secret_key"],))
    summary=""
    if s["technique_use_count"]:
        k,n=max(s["technique_use_count"].items(),key=lambda x:x[1]); summary=f"\n\n你這局最常用《{tech_name(k)}》（{n} 次），它確實改變了公司後續如何對付你。"
    s["ending"]={"title":q["title"],"body":q["body"]+summary,"secret_title":s["secret_title"]}

def relationship_label(v): return "明顯站在你這邊" if v>=4 else "開始信任你" if v>=2 else "對你非常戒備" if v<=-3 else "有點不爽你" if v<=-1 else "還在觀察你"
def active_character_cards(s): return [{"name":s["active_characters"][r]["short_name"],"job":s["active_characters"][r]["job"],"relationship":relationship_label(s["relationships"].get(r,0)),"hook":s["active_characters"][r]["comic_hook"]} for r in s["active_roles"]]
def owned_techniques(s):
    if not s["techniques"]:return []
    ph=",".join("?" for _ in s["techniques"]); arr=[dict(x) for x in rows(f"SELECT * FROM techniques WHERE tech_key IN ({ph})",tuple(s["techniques"]))]
    for t in arr:
        p=profile(t["tech_key"]); t["use_count"]=s["technique_use_count"].get(t["tech_key"],0); t["persistent_effect"]=p["persistent_effect"] if p else ""; t["countered"]=t["tech_key"] in s["technique_countered"]
    return arr
