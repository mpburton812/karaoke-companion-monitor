import os
import asyncio
import time
import pandas as pd
from typing import List, Dict, Any, Optional
import libsql_client
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.url = os.getenv("LIBSQL_URL")
        # Ensure we use https if libsql:// is provided to avoid 505 protocol errors
        if self.url and self.url.startswith("libsql://"):
            self.url = self.url.replace("libsql://", "https://", 1)
        self.auth_token = os.getenv("LIBSQL_AUTH_TOKEN")
        self.client: Optional[libsql_client.Client] = None

    async def connect(self):
        if not self.client:
            self.client = libsql_client.create_client(self.url, auth_token=self.auth_token)

    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None

    async def check_health(self) -> Dict[str, Any]:
        if not self.client:
            await self.connect()
        
        start_time = time.perf_counter()
        try:
            await self.client.execute("SELECT 1")
            latency = (time.perf_counter() - start_time) * 1000
            return {"status": "Online", "latency": f"{latency:.2f}ms"}
        except Exception as e:
            return {"status": "Offline", "error": str(e)}

    async def get_user_stats(self) -> List[Dict[str, Any]]:
        if not self.client:
            await self.connect()

        query = """
        SELECT 
            u.username,
            MIN(COALESCE(p.date, s.last_practiced, sl.created_at)) as created_approx,
            MAX(COALESCE(p.date, s.last_practiced)) as last_used_approx,
            COUNT(DISTINCT p.date) as total_uses,
            COUNT(DISTINCT s.id) as songs_count,
            COUNT(DISTINCT l.id) as venues_count,
            COUNT(DISTINCT t.id) as tags_count
        FROM users u
        LEFT JOIN songs s ON u.id = s.user_id
        LEFT JOIN performances p ON u.id = p.user_id
        LEFT JOIN locations l ON u.id = l.user_id
        LEFT JOIN tags t ON u.id = t.user_id
        LEFT JOIN setlists sl ON u.id = sl.user_id
        GROUP BY u.id, u.username
        """
        try:
            result = await self.client.execute(query)
            columns = [col for col in result.columns]
            stats = []
            for row in result.rows:
                stats.append(dict(zip(columns, row)))
            return stats
        except Exception as e:
            print(f"Error fetching user stats: {e}")
            return []

    async def get_recent_performances(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.client:
            await self.connect()

        query = f"""
        SELECT 
            p.date,
            p.time,
            u.username,
            s.track_name,
            s.artist_name,
            p.location,
            p.rating
        FROM performances p
        JOIN users u ON p.user_id = u.id
        JOIN songs s ON p.song_id = s.id
        ORDER BY p.date DESC, p.time DESC
        LIMIT {limit}
        """
        try:
            result = await self.client.execute(query)
            columns = [col for col in result.columns]
            performances = []
            for row in result.rows:
                performances.append(dict(zip(columns, row)))
            return performances
        except Exception as e:
            print(f"Error fetching recent performances: {e}")
            return []

    async def get_upcoming_songs(self, limit: int = 10) -> List[Dict[str, Any]]:
        # This assumes there's a setlist representing the queue, 
        # for now let's just fetch from the most recent setlist
        if not self.client:
            await self.connect()

        query = f"""
        SELECT 
            u.username,
            s.track_name,
            s.artist_name,
            sl.name as setlist_name
        FROM setlist_songs ss
        JOIN songs s ON ss.song_id = s.id
        JOIN setlists sl ON ss.setlist_id = sl.id
        JOIN users u ON sl.user_id = u.id
        ORDER BY sl.created_at DESC, ss.display_order ASC
        LIMIT {limit}
        """
        try:
            result = await self.client.execute(query)
            columns = [col for col in result.columns]
            upcoming = []
            for row in result.rows:
                upcoming.append(dict(zip(columns, row)))
            return upcoming
        except Exception as e:
            print(f"Error fetching upcoming songs: {e}")
            return []

    async def get_user_details(self, username: str) -> Dict[str, List[str]]:
        if not self.client:
            await self.connect()

        # Get user ID first
        try:
            user_res = await self.client.execute("SELECT id FROM users WHERE username = ?", [username])
            if not user_res.rows:
                return {"songs": [], "venues": [], "tags": []}
            user_id = user_res.rows[0][0]

            # Fetch Songs
            songs_res = await self.client.execute("SELECT track_name || ' - ' || artist_name FROM songs WHERE user_id = ? ORDER BY track_name", [user_id])
            songs = [row[0] for row in songs_res.rows]

            # Fetch Venues
            venues_res = await self.client.execute("SELECT name FROM locations WHERE user_id = ? ORDER BY name", [user_id])
            venues = [row[0] for row in venues_res.rows]

            # Fetch Tags
            tags_res = await self.client.execute("SELECT name FROM tags WHERE user_id = ? ORDER BY name", [user_id])
            tags = [row[0] for row in tags_res.rows]

            return {"songs": songs, "venues": venues, "tags": tags}
        except Exception as e:
            print(f"Error fetching user details for {username}: {e}")
            return {"songs": [], "venues": [], "tags": []}
