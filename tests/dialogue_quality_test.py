
import sqlite3
from game.db import DB_PATH
from game.engine import new_game, ensure_scene, options_for_scene, choose

with sqlite3.connect(DB_PATH) as conn:
    assert conn.execute("SELECT COUNT(*) FROM choice_dialogue_meta").fetchone()[0] >= 900
    assert conn.execute("SELECT COUNT(*) FROM role_response_templates").fetchone()[0] >= 100
    assert conn.execute("SELECT COUNT(*) FROM role_voice_lines_v2").fetchone()[0] >= 100

unique_npc=set()
for seed in range(25):
    s=new_game("測試新人",seed)
    n=0
    while not s.get("ending"):
        ensure_scene(s)
        opts=options_for_scene(s)
        assert opts
        choose(s,opts[seed%len(opts)])
        q=s["dialogue_queue"]
        assert 2<=len(q)<=4
        assert q[0]["kind"]=="player"
        assert q[0]["speaker"]=="測試新人"
        npcs=[x for x in q if x["kind"]=="npc"]
        assert npcs
        for x in npcs:
            assert len(x["text"])>=8
            unique_npc.add(x["text"])
        s["dialogue_pending"]=False
        n+=1
        assert n<=24
    assert s["turn"]==18
assert len(unique_npc)>=100
print("V4.5 dialogue quality test passed:",len(unique_npc),"unique NPC lines")
