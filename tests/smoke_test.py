
from game.engine import new_game,ensure_scene,options_for_scene,choose
for seed in range(30):
 s=new_game("測試",seed); fam=[]; n=0
 while not s.get("ending"):
  sc=ensure_scene(s)
  if not sc["family"].startswith(("tech_consequence_","combo_consequence_")): fam.append(sc["family"])
  opts=options_for_scene(s); assert opts
  labs=[o.get("label",o.get("option_label")) for o in opts]; assert len(labs)==len(set(labs))
  choose(s,opts[seed%len(opts)]); s["dialogue_pending"]=False; n+=1; assert n<=20
 assert s["turn"]==15 and s["ending"]; assert len(fam)==len(set(fam))
print("V4.6 smoke test passed")
