import sqlite3

conn = sqlite3.connect('monitor.db')
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

print("Tabelas existentes no banco:")
for table in tables:
    print(f"  - {table[0]}")

conn.close()
