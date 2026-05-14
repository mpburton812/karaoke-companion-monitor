import os
import psutil
import time
from typing import Dict, Any, List

class MonitorEngine:
    def __init__(self, log_file_path: str = None):
        self.log_file_path = log_file_path
        self._last_log_position = 0
        if self.log_file_path and os.path.exists(self.log_file_path):
            self._last_log_position = os.path.getsize(self.log_file_path)

    def get_system_metrics(self) -> Dict[str, float]:
        """Returns CPU and RAM usage percentages."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent
        }

    def get_new_log_lines(self) -> List[str]:
        """Reads new lines from the log file since the last call."""
        if not self.log_file_path or not os.path.exists(self.log_file_path):
            return []

        new_lines = []
        try:
            current_size = os.path.getsize(self.log_file_path)
            if current_size < self._last_log_position:
                # File was likely rotated or truncated
                self._last_log_position = 0

            with open(self.log_file_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_log_position)
                new_lines = f.readlines()
                self._last_log_position = f.tell()
        except Exception as e:
            new_lines = [f"Error reading log file: {e}"]
        
        return [line.strip() for line in new_lines if line.strip()]

    def set_log_file_path(self, path: str):
        self.log_file_path = path
        if path and os.path.exists(path):
            self._last_log_position = os.path.getsize(path)
        else:
            self._last_log_position = 0
