import asyncio
import os
from dotenv import load_dotenv
from db import DatabaseManager

async def test_connection():
    load_dotenv()
    url = os.getenv("LIBSQL_URL")
    token = os.getenv("LIBSQL_AUTH_TOKEN")
    
    print(f"Attempting to connect to: {url}")
    if not token:
        print("Warning: LIBSQL_AUTH_TOKEN is not set.")
    else:
        print("LIBSQL_AUTH_TOKEN is set.")

    db = DatabaseManager()
    health = await db.check_health()
    print(f"Health Check Result: {health}")
    
    if health['status'] == 'Online':
        print("Success! Testing a simple query...")
        try:
            stats = await db.get_user_stats()
            print(f"Fetched {len(stats)} users.")
        except Exception as e:
            print(f"Query failed: {e}")
    else:
        print(f"Connection failed: {health.get('error')}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
