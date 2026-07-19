from game.engine import new_game,ensure_scene,options_for_scene,choose
for seed in range(25):
 s=new_game('測試',seed); fam=[]; guard=0
 while not s.get('ending'):
  sc=ensure_scene(s); fam.append(sc['family']); opts=options_for_scene(s); assert opts; labels=[o.get('label',o.get('option_label')) for o in opts]; assert len(labels)==len(set(labels)); choose(s,opts[seed%len(opts)]); guard+=1; assert guard<=24
 nf=[x for x in fam if not x.startswith('fallout_')]; assert len(nf)==len(set(nf)); assert s['turn']==18 and s['ending']
print('V4.2 smoke test passed: 25 complete runs')
