import sqlite3

conn = sqlite3.connect("fabric.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE fabrics (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
cost_price REAL,
selling_price REAL,
quantity INTEGER
)
""")

cursor.execute("""
CREATE TABLE sales (
id INTEGER PRIMARY KEY AUTOINCREMENT,
fabric_id INTEGER,
quantity INTEGER,
revenue REAL,
profit REAL,
date TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully")