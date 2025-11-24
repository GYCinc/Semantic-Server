import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

# Carlos's account
student_data = {
    "username": "carlos",
    "password_hash": "carlos-premium-english-2025",
    "first_name": "Carlos",
    "last_name": "",
    "email": "carlos@example.com"
}

try:
    # Check if exists first
    existing = supabase.table("students").select("*").eq("username", "carlos").execute()
    
    if existing.data and len(existing.data) > 0:
        # Update existing
        response = supabase.table("students").update({
            "password_hash": "carlos-premium-english-2025"
        }).eq("username", "carlos").execute()
        print(f"✅ Updated Carlos's access code!")
        print(f"   Access Code: carlos-premium-english-2025")
        print(f"   Student ID: {existing.data[0]['id']}")
    else:
        # Create new
        response = supabase.table("students").insert(student_data).execute()
        if response.data and len(response.data) > 0:
            print(f"✅ Created Carlos's account!")
            print(f"   Access Code: carlos-premium-english-2025")
            print(f"   Student ID: {response.data[0]['id']}")
        else:
            print("❌ Failed to create student")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
