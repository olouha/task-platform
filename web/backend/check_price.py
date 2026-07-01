import sqlite3
conn = sqlite3.connect("data/yantai_rebar.db")
cursor = conn.cursor()

cursor.execute("SELECT date, price, material_type, spec FROM rebar_prices WHERE date LIKE '2024-01%' LIMIT 10")
print("2024年1月数据样本:")
for row in cursor.fetchall():
    print(f"  {row[0]}: price={row[1]}, type={row[2]}, spec={row[3]}")

cursor.execute("SELECT COUNT(*) FROM rebar_prices WHERE price IS NULL")
print()
print("价格为NULL:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM rebar_prices WHERE price IS NOT NULL")
print("价格有值:", cursor.fetchone()[0])

conn.close()
