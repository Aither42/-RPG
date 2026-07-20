
from game.engine import new_game,ensure_scene,options_for_scene,choose
u=set()
for seed in range(20):
 s=new_game("測試新人",seed); n=0
 while not s.get("ending"):
  ensure_scene(s); opts=options_for_scene(s); choose(s,opts[seed%len(opts)])
  q=s["dialogue_queue"]; assert 2<=len(q)<=4 and q[0]["kind"]=="player"
  for x in q:
   if x["kind"]=="npc":u.add(x["text"])
  s["dialogue_pending"]=False; n+=1; assert n<=20
 assert s["turn"]==15
assert len(u)>=120
print("V4.6 dialogue quality test passed",len(u))
