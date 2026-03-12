import sqlite3

conn = sqlite3.connect("govtech_complaints.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE complaints ADD COLUMN latitude REAL")
    cursor.execute("ALTER TABLE complaints ADD COLUMN longitude REAL")
    print("✅ GPS Columns added to Database.")
except:
    print("ℹ️ Columns already exist.")

conn.commit()
conn.close()