
import sqlite3
from game.db import DB_PATH
from game.engine import TOTAL_TURNS,new_game,ensure_scene,options_for_scene,choose

assert TOTAL_TURNS == 18

with sqlite3.connect(DB_PATH) as c:
    assert c.execute("SELECT COUNT(*) FROM characters WHERE is_core=1").fetchone()[0] == 12
    assert c.execute("SELECT COUNT(*) FROM characters WHERE is_core=0").fetchone()[0] == 8
    assert c.execute("SELECT COUNT(*) FROM world_secrets").fetchone()[0] == 8

required_core={
    'guard','rookie','manager','hr','friend','ceo',
    'finance','legal','it','general','courier','cafe'
}

for seed in range(20):
    s=new_game('測試新人',seed)
    assert len(s['active_roles']) == 18
    assert len(set(s['active_roles'])) == 18
    assert required_core.issubset(set(s['active_roles']))
    n=0
    while not s.get('ending'):
        sc=ensure_scene(s)
        opts=options_for_scene(s)
        assert opts
        choose(s,opts[0])
        n+=1
        assert n<=24
    assert s['turn']==18
    assert s['ending']

print('V4.2 configuration test passed: 20 complete runs')
