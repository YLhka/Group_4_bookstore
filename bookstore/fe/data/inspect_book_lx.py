import sqlite3
import os
from pathlib import Path

DB_PATH = r"D:\华师大\大三\当代数据管理系统\大作业1\Bookstore\bookstore\fe\data\book_lx.db"

if not os.path.exists(DB_PATH):
    raise FileNotFoundError(f"找不到这个文件，请检查路径：{DB_PATH}")

# 连上去
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 看看里面有什么表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("tables:", tables)

# 把每张表的结构打出来
for t in tables:
    print(f"\n=== table: {t} ===")
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    for cid, name, ctype, notnull, dflt, pk in cols:
        print(f"  {name} {ctype} {'PRIMARY KEY' if pk else ''}")

conn.close()
