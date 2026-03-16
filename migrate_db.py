import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'paws_core.db')
print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE incidents ADD COLUMN raw_nova_json TEXT")
    conn.commit()
    print("Column added successfully.")
except sqlite3.OperationalError as e:
    print(f"Operational error: {e}")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
