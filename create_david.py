import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
    exit(1)

supabase: Client = create_client(url, key)

async def create_david():
    print("Creating student account for David...")
    
    # Check if user already exists
    username = "david-saves-snacks-2025"
    
    try:
        # Check for existing user
        existing = supabase.table("students").select("*").eq("username", username).execute()
        
        if existing.data:
            print(f"User {username} already exists. Updating...")
            # Update existing
            data = {
                "first_name": "David",
                "last_name": "Student",
                "email": "david@example.com",
                "password_hash": username, # Must match username for single-field login
            }
            response = supabase.table("students").update(data).eq("username", username).execute()
        else:
            print(f"Creating new user {username}...")
            # Create new
            data = {
                "username": username,
                "first_name": "David",
                "last_name": "Student",
                "email": "david@example.com",
                "password_hash": username,
            }
            response = supabase.table("students").insert(data).execute()
            
        print(f"Successfully created/updated David: {response.data}")
        
    except Exception as e:
        print(f"Error creating David: {e}")

if __name__ == "__main__":
    asyncio.run(create_david())
