import sqlite3
conn = sqlite3.connect("services/data/yantai_rebar_backup.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM rebar_prices WHERE price IS NOT NULL")
print("备份DB有效数据:", cursor.fetchone()[0])

cursor.execute("SELECT substr(date,1,4), COUNT(*) FROM rebar_prices WHERE price IS NOT NULL GROUP BY substr(date,1,4)")
print("各年份:")
for row in cursor.fetchall():
    print(f"  {row[0]}年: {row[1]}条")

# 看看实际数据
cursor.execute("SELECT date, price, material_type, spec FROM rebar_prices WHERE price IS NOT NULL LIMIT 10")
print()
print("样本数据:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}元 | {row[2]} | {row[3]}")

conn.close()
