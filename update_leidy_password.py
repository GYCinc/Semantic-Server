import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

# User-specified access code
new_code = "leidy-2025-wallyworld"

try:
    response = supabase.table("students").update({
        "password_hash": new_code
    }).eq("username", "leidy").execute()
    
    if response.data and len(response.data) > 0:
        print(f"✅ Updated Leidy's access code!")
        print(f"   Access Code: {new_code}")
        print(f"   Student ID: {response.data[0]['id']}")
    else:
        print("❌ Failed to update")

except Exception as e:
    print(f"❌ Error: {e}")
