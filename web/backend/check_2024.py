import sqlite3
conn = sqlite3.connect("data/yantai_rebar.db")
cursor = conn.cursor()

cursor.execute("SELECT substr(date,1,4), COUNT(*) FROM rebar_prices GROUP BY substr(date,1,4)")
print("各年份:")
for row in cursor.fetchall():
    print(f"  {row[0]}年: {row[1]}条")

# 检查2024年数据
cursor.execute("SELECT date, price, material_type, spec FROM rebar_prices WHERE date LIKE \"2024%\" LIMIT 20")
print()
print("2024年样本:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}元 | {row[2]} | {row[3]}")

conn.close()
