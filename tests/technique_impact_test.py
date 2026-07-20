
from game.engine import new_game,ensure_scene,options_for_scene,choose
s=new_game("功法測試",7)
s["techniques"]=["seen_silence","excel_sword","ppt_dragon","meeting_soul","coat_clone"]
used=False; ripple=False; follow=False; combo=False; n=0
while not s.get("ending"):
 sc=ensure_scene(s)
 if "【功法餘波" in sc.get("extra_line",""):ripple=True
 if sc["family"].startswith(("tech_consequence_","combo_consequence_")):follow=True
 opts=options_for_scene(s); assert opts
 pick=next((o for o in opts if o.get("is_combo")),None)
 if pick: combo=True
 if pick is None: pick=next((o for o in opts if o.get("is_technique")),None)
 if pick and pick.get("is_technique"): used=True
 if pick is None:pick=opts[0]
 choose(s,pick); s["dialogue_pending"]=False; n+=1; assert n<=20
assert s["turn"]==15 and s["ending"]
assert used or combo
assert s["technique_use_count"] or s["used_combos"]
assert ripple or follow or s["used_combos"]
print("V4.6 technique impact test passed",used,combo,ripple,follow)
