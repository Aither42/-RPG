from game.engine import new_game,ensure_scene,options_for_scene,choose
seen=False
for seed in range(50):
 s=new_game('測試',1000+seed)
 while not s.get('ending'):
  sc=ensure_scene(s); opts=options_for_scene(s)
  for o in opts:
   if o.get('is_technique'):
    seen=True; assert o['tech_key'] in s['techniques']; assert o['scene_tag'] in sc.get('tags',[])
  choose(s,opts[0])
assert seen
print('V4.2 coherence test passed')
