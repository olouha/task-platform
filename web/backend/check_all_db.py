import sqlite3

for db_name in ['yantai_rebar.db', 'yantai_rebar_broken.db', 'yantai_rebar_new.db', 'yantai_rebar_old.db']:
    try:
        conn = sqlite3.connect(f"services/data/{db_name}")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rebar_prices WHERE price IS NOT NULL")
        valid = cursor.fetchone()[0]
        cursor.execute("SELECT substr(date,1,4), COUNT(*) FROM rebar_prices WHERE price IS NOT NULL GROUP BY substr(date,1,4)")
        years = [f"{r[0]}年:{r[1]}条" for r in cursor.fetchall()]
        print(f"{db_name}:")
        print(f"  有效数据: {valid}")
        print(f"  年份: {years}")
        conn.close()
    except Exception as e:
        print(f"{db_name}: Error - {e}")
