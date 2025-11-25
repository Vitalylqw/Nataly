"""Check what's in the database."""
import sqlite3
from pathlib import Path

db_path = Path("var/app.db")

if not db_path.exists():
    print(f"Database not found at {db_path}")
else:
    print(f"Database found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Check transcripts
    cursor = conn.execute("SELECT * FROM transcripts ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    
    print(f"\nFound {len(rows)} recent transcripts:")
    for row in rows:
        print(f"\n  Hash: {row['file_hash'][:16]}...")
        print(f"  Language: {row['language']}")
        print(f"  Provider: {row['provider']}")
        print(f"  Created: {row['created_at']}")
        print(f"  Text preview: {row['text'][:100]}...")
    
    conn.close()
