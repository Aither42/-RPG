
import sqlite3
from game.db import DB_PATH

with sqlite3.connect(DB_PATH) as conn:
    assert conn.execute(
        "SELECT COUNT(*) FROM character_profiles_v4"
    ).fetchone()[0] == 20
    assert conn.execute(
        "SELECT COUNT(*) FROM character_emotion_lines_v4"
    ).fetchone()[0] == 1080
    assert conn.execute(
        "SELECT COUNT(DISTINCT family) FROM events WHERE act=1 AND is_finale=0"
    ).fetchone()[0] >= 20
    assert conn.execute(
        "SELECT COUNT(*) FROM choice_dialogue_variants_v4"
    ).fetchone()[0] >= 4000

print("V4.7 profile/data test passed")
