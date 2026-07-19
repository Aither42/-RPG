from pathlib import Path
import sqlite3
DB_PATH=Path(__file__).resolve().parents[1]/'data'/'game_v4.db'
def connect():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
