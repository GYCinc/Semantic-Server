import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

print(f"Python: {sys.version}")
print("Checking imports...")

try:
    import assemblyai
    print("✅ assemblyai imported")
except ImportError as e:
    print(f"❌ assemblyai missing: {e}")

try:
    from supabase import create_client
    print("✅ supabase imported")
except ImportError as e:
    print(f"❌ supabase missing: {e}")

print("\nChecking Supabase Connection...")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY in .env")
else:
    print(f"URL found: {url[:10]}...")
    try:
        supabase = create_client(url, key)
        # Try a simple query - just get count of students or something lightweight
        # We'll just check if we can access the table object, actual network call might fail if no internet but usually this env has internet
        print("✅ Supabase client initialized")
        
        # Optional: Try a real ping
        # response = supabase.table("students").select("count", count="exact").execute()
        # print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Supabase init failed: {e}")
