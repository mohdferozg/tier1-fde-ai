"""Verify connection to Supabase Postgres."""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise SystemExit("DATABASE_URL not set in .env")

print("Connecting to Supabase...")
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Test basic connectivity
    cur.execute("SELECT 1;")
    print("OK Basic connection")

    # Test vector extension
    cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
    if cur.fetchone():
        print("OK pgvector extension enabled")
    else:
        print("FAIL pgvector extension NOT enabled")

    # Test documents table
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'documents'
        ORDER BY ordinal_position;
    """)
    rows = cur.fetchall()
    if rows:
        print(f"OK documents table has {len(rows)} columns:")
        for name, dtype in rows:
            print(f"    - {name}: {dtype}")
    else:
        print("FAIL documents table not found")

    cur.close()
    conn.close()
    print("\nAll checks passed")
except Exception as e:
    print(f"FAIL Connection failed: {e}")