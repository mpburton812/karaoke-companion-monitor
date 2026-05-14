import os
import psutil
import time
import requests
from typing import Dict, Any, List

class MonitorEngine:
    def __init__(self, log_file_path: str = None):
        self.log_file_path = log_file_path
        self._last_log_position = 0
        if self.log_file_path and os.path.exists(self.log_file_path):
            self._last_log_position = os.path.getsize(self.log_file_path)
            
        # Render API configuration
        self.render_api_key = os.getenv("RENDER_API_KEY")
        self.render_service_id = os.getenv("RENDER_SERVICE_ID")
        self.render_owner_id = None
        self._last_render_log_time = None

    def get_system_metrics(self) -> Dict[str, float]:
        """Returns CPU and RAM usage percentages."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent
        }

    def _ensure_render_owner_id(self) -> bool:
        """Fetches the ownerId for the service if not already known."""
        if self.render_owner_id:
            return True
        
        if not self.render_api_key or not self.render_service_id:
            return False

        try:
            url = f"https://api.render.com/v1/services/{self.render_service_id}"
            headers = {"Authorization": f"Bearer {self.render_api_key}"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                self.render_owner_id = response.json().get("ownerId")
                return True
        except Exception as e:
            print(f"Error fetching Render ownerId: {e}")
        return False

    def get_new_log_lines(self) -> List[str]:
        """Reads new lines from Render API or local log file."""
        if self.render_api_key and self.render_service_id:
            if self._ensure_render_owner_id():
                return self._get_render_logs()
        
        if not self.log_file_path or not os.path.exists(self.log_file_path):
            return []

        new_lines = []
        try:
            current_size = os.path.getsize(self.log_file_path)
            if current_size < self._last_log_position:
                self._last_log_position = 0

            with open(self.log_file_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_log_position)
                new_lines = f.readlines()
                self._last_log_position = f.tell()
        except Exception as e:
            new_lines = [f"Error reading local log file: {e}"]
        
        return [line.strip() for line in new_lines if line.strip()]

    def _get_render_logs(self) -> List[str]:
        """Fetches logs from the Render API using the correct v1/logs endpoint."""
        url = f"https://api.render.com/v1/logs"
        params = {
            "ownerId": self.render_owner_id,
            "resource": self.render_service_id,
            "limit": 20,
            "direction": "backward"
        }
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.render_api_key}"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                logs_data = response.json()
                new_entries = []
                
                # Render v1/logs returns a list of log objects
                # We want to show them in chronological order, so we reverse the 'backward' list
                for entry in reversed(logs_data):
                    timestamp = entry.get("timestamp")
                    text = entry.get("text", "").strip()
                    
                    if not self._last_render_log_time or timestamp > self._last_render_log_time:
                        if text:
                            new_entries.append(f"[{timestamp}] {text}")
                        self._last_render_log_time = timestamp
                
                return new_entries
            else:
                return [f"Render API Error ({response.status_code}): {response.text}"]
        except Exception as e:
            return [f"Exception fetching Render logs: {e}"]

    def set_log_file_path(self, path: str):
        self.log_file_path = path
        if path and os.path.exists(path):
            self._last_log_position = os.path.getsize(path)
        else:
            self._last_log_position = 0
