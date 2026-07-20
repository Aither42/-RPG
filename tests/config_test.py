
import sqlite3
from game.db import DB_PATH
from game.engine import TOTAL_TURNS,new_game
assert TOTAL_TURNS==15
with sqlite3.connect(DB_PATH) as c:
 assert c.execute("select count(*) from choice_dialogue_variants_v3").fetchone()[0]==2916
 assert c.execute("select count(*) from role_response_templates_v3").fetchone()[0]==360
 assert c.execute("select count(*) from role_voice_lines_v3").fetchone()[0]==360
 assert c.execute("select count(*) from technique_effect_profiles_v3").fetchone()[0]==120
 assert c.execute("select count(*) from technique_role_reactions_v3").fetchone()[0]==4800
s=new_game("測試",42); assert len(s["active_roles"])==18
print("V4.6 config test passed")
