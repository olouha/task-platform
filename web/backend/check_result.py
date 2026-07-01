import sqlite3
conn = sqlite3.connect("data/yantai_rebar.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM rebar_prices")
print("总记录数:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM rebar_prices WHERE price IS NULL")
print("价格为NULL:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM rebar_prices WHERE price IS NOT NULL")
print("价格有值:", cursor.fetchone()[0])

# 检查各年份
cursor.execute("SELECT substr(date,1,4), COUNT(*) FROM rebar_prices GROUP BY substr(date,1,4)")
print()
print("各年份数据:")
for row in cursor.fetchall():
    print(f"  {row[0]}年: {row[1]}条")

# 样本数据
cursor.execute("SELECT date, price, material_type, spec FROM rebar_prices LIMIT 10")
print()
print("样本数据:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}元 | {row[2]} | {row[3]}")

conn.close()
