import sqlite3
conn = sqlite3.connect("data/yantai_rebar.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")
tables = cursor.fetchall()
print("表:", [t[0] for t in tables])

if tables:
    cursor.execute("SELECT COUNT(*) FROM rebar_prices WHERE price IS NOT NULL")
    print("有效数据:", cursor.fetchone()[0])

conn.close()
