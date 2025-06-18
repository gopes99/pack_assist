import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS credentials (
    username TEXT PRIMARY KEY,
    credential_id BLOB NOT NULL,
    public_key BLOB NOT NULL
)
""")

print("Database created.")
conn.commit()
conn.close()
