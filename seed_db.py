import sqlite3
import pandas as pd
import uuid
from datetime import datetime
import random

# 1. Load Excel
try:
    df = pd.read_excel("mock_data.xlsx", sheet_name="Sheet1") 
    print(f"✅ Loaded {len(df)} rows from Excel.")
except Exception as e:
    print(f"❌ Excel Error: {e}")
    exit()

# 2. Connect & Check Schema
conn = sqlite3.connect("govtech_complaints.db")
cursor = conn.cursor()

# Ensure GPS columns exist
try:
    cursor.execute("ALTER TABLE complaints ADD COLUMN latitude REAL")
    cursor.execute("ALTER TABLE complaints ADD COLUMN longitude REAL")
except:
    pass # Columns already exist

cursor.execute("PRAGMA table_info(complaints)")
db_cols = [info[1] for info in cursor.fetchall()]

# Clear old random data for a clean demo
cursor.execute("DELETE FROM complaints")

print("🚀 Force-injecting Nagpur data with REAL GPS coordinates...")

success_count = 0
for index, row in df.iterrows():
    try:
        comp_id = f"CMP-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.utcnow().isoformat() + "Z"
        
        # Add a tiny 'jitter' so overlapping complaints spread out slightly (approx 10-20 meters)
        lat_jitter = row['latitude'] + random.uniform(-0.0005, 0.0005)
        lon_jitter = row['longitude'] + random.uniform(-0.0005, 0.0005)
        
        # Prepare the data mapping from YOUR Excel headers
        data = {
            "id": comp_id,
            "original_text": f"[{str(row['area'])}] {str(row['complaint'])}",
            "translated_text": str(row['complaint']),
            "category": str(row['category']).upper(),
            "priority": str(row['priority']).upper(),
            "status": str(row['status']).upper(),
            "summary": str(row['complaint'])[:50],
            "submitted_at": now,
            "updated_at": now,
            "latitude": lat_jitter,
            "longitude": lon_jitter
        }

        # Dynamically build the query based on existing columns
        final_data = {k: v for k, v in data.items() if k in db_cols}
        columns = ', '.join(final_data.keys())
        placeholders = ', '.join(['?'] * len(final_data))
        
        query = f"INSERT INTO complaints ({columns}) VALUES ({placeholders})"
        cursor.execute(query, list(final_data.values()))
        success_count += 1
        
    except Exception as e:
        print(f"⚠️ Row {index} failed: {e}")

conn.commit()
conn.close()

print(f"\n🎉 MISSION ACCOMPLISHED! Added {success_count} complaints with real GPS.")