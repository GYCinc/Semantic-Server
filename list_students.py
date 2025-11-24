import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ Missing credentials")
else:
    try:
        supabase = create_client(url, key)
        res = supabase.table("students").select("username, first_name").execute()
        print("\n📋 Available Students in Database:")
        if res.data:
            for s in res.data:
                print(f" - Username: {s.get('username')} | Name: {s.get('first_name')}")
        else:
            print(" (No students found)")
        print("\n💡 Use one of these names in the Semantic Surfer app to ensure analysis is saved.")
    except Exception as e:
        print(f"❌ Error: {e}")
