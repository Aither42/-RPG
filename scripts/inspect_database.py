from pathlib import Path
import sqlite3
db=Path(__file__).resolve().parents[1]/'data'/'game_v4.db';c=sqlite3.connect(db)
for t in ['characters','world_secrets','techniques','technique_uses','events','choices','character_reactions','ambient_responses','endings']:
 print(f'{t}: {c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]:,}')
print(f'DB size: {db.stat().st_size/1024/1024:.2f} MB')
