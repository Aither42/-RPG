
from game.engine import new_game,ensure_scene,options_for_scene,choose

total=0
for seed in range(20):
    s=new_game('測試新人',seed)
    guard=0
    while not s.get('ending'):
        ensure_scene(s)
        opts=options_for_scene(s)
        assert opts
        choose(s,opts[0])
        assert s.get('dialogue_pending') is True
        q=s.get('dialogue_queue',[])
        assert 2<=len(q)<=4
        assert q[0]['speaker']=='測試新人'
        assert q[0]['kind']=='player'
        assert any(x['kind']=='npc' for x in q[1:])
        for x in q:
            assert x['speaker']
            assert x['text']
        total+=len(q)
        s['dialogue_pending']=False
        guard+=1
        assert guard<=24
    assert s['turn']==18
assert total>500
print('V4.4 dialogue test passed:',total,'subtitle lines')
