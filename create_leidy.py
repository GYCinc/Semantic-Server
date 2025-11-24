import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ Missing Supabase credentials")
    exit(1)

supabase = create_client(url, key)

student_data = {
    "username": "leidy",
    "password_hash": "leidy",  # Simple access code (username and password are the same)
    "first_name": "Leidy",
    "last_name": "",
    "email": "leidy@example.com"
}

try:
    # Check if exists first
    existing = supabase.table("students").select("*").eq("username", "leidy").execute()
    
    if existing.data and len(existing.data) > 0:
        print(f"✅ Student 'Leidy' already exists!")
        print(f"   ID: {existing.data[0]['id']}")
        print(f"   Access Code: leidy")
        print(f"   Dashboard URL: http://localhost:3000/student/{existing.data[0]['id']}/dashboard")
    else:
        response = supabase.table("students").insert(student_data).execute()
        if response.data and len(response.data) > 0:
            print(f"✅ Created student 'Leidy'!")
            print(f"   ID: {response.data[0]['id']}")
            print(f"   Access Code: leidy")
            print(f"   Dashboard URL: http://localhost:3000/student/{response.data[0]['id']}/dashboard")
        else:
            print("❌ Failed to create student")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
