import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS credentials (
    username TEXT PRIMARY KEY,
    credential_id BLOB NOT NULL,
    public_key BLOB NOT NULL
);
-- credentials table
CREATE TABLE credentials (
    username TEXT PRIMARY KEY,
    credential_id BLOB,
    public_key BLOB
);

-- containers table
CREATE TABLE containers (
    id TEXT PRIMARY KEY,
    content BLOB
);

""")




print("Database created.")
conn.commit()
conn.close()
