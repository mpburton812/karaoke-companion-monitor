import os
import asyncio
import threading
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any

from db import DatabaseManager
from monitor_engine import MonitorEngine

load_dotenv()

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AsyncHandler:
    """Helper to run async tasks from a sync environment."""
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

class KaraokeMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Karaoke Companion Monitor")
        self.geometry("1100x700")

        # Initialize Managers
        self.db_manager = DatabaseManager()
        self.monitor_engine = MonitorEngine(os.getenv("LOG_FILE_PATH"))
        self.async_handler = AsyncHandler()

        # UI State
        self.current_tab = "Dashboard"
        
        # Grid layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_main_frames()
        
        # Start polling
        self.poll_updates()
        self.poll_db_updates()

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="KARAOKE\nMONITOR", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.db_status_label = ctk.CTkLabel(self.sidebar_frame, text="DB: Checking...", text_color="gray")
        self.db_status_label.grid(row=1, column=0, padx=20, pady=5)

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=lambda: self.select_frame("Dashboard"))
        self.sidebar_button_1.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="User Stats", command=lambda: self.select_frame("User Stats"))
        self.sidebar_button_2.grid(row=3, column=0, padx=20, pady=10)

        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Logs", command=lambda: self.select_frame("Logs"))
        self.sidebar_button_3.grid(row=4, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

    def setup_main_frames(self):
        # Dashboard Frame
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_dashboard_ui()

        # User Stats Frame
        self.user_stats_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_user_stats_ui()

        # Logs Frame
        self.logs_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_logs_ui()

        # Default frame
        self.select_frame("Dashboard")

    def setup_dashboard_ui(self):
        self.dashboard_frame.grid_columnconfigure((0, 1), weight=1)
        self.dashboard_frame.grid_rowconfigure(2, weight=1)

        # Resource Bars
        self.resource_frame = ctk.CTkFrame(self.dashboard_frame)
        self.resource_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        self.resource_frame.grid_columnconfigure((0, 1), weight=1)

        self.cpu_label = ctk.CTkLabel(self.resource_frame, text="CPU Usage: 0%")
        self.cpu_label.grid(row=0, column=0, padx=20, pady=(10, 0))
        self.cpu_progress = ctk.CTkProgressBar(self.resource_frame)
        self.cpu_progress.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.cpu_progress.set(0)

        self.ram_label = ctk.CTkLabel(self.resource_frame, text="RAM Usage: 0%")
        self.ram_label.grid(row=0, column=1, padx=20, pady=(10, 0))
        self.ram_progress = ctk.CTkProgressBar(self.resource_frame)
        self.ram_progress.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")
        self.ram_progress.set(0)

        # Recent Performances
        self.recent_perf_label = ctk.CTkLabel(self.dashboard_frame, text="Recent Performances", font=ctk.CTkFont(size=16, weight="bold"))
        self.recent_perf_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")

        self.recent_perf_list = ctk.CTkTextbox(self.dashboard_frame, height=200)
        self.recent_perf_list.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        # Upcoming Songs
        self.upcoming_songs_label = ctk.CTkLabel(self.dashboard_frame, text="Upcoming Songs (from Setlists)", font=ctk.CTkFont(size=16, weight="bold"))
        self.upcoming_songs_label.grid(row=1, column=1, padx=20, pady=(10, 0), sticky="w")

        self.upcoming_songs_list = ctk.CTkTextbox(self.dashboard_frame, height=200)
        self.upcoming_songs_list.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")

    def setup_user_stats_ui(self):
        self.user_stats_frame.grid_columnconfigure(0, weight=1)
        self.user_stats_frame.grid_rowconfigure(1, weight=1)

        self.user_stats_title = ctk.CTkLabel(self.user_stats_frame, text="User Statistics", font=ctk.CTkFont(size=20, weight="bold"))
        self.user_stats_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Use a standard tkinter Treeview for the table since ctk doesn't have one
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        self.style.map("Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(self.user_stats_frame, columns=("username", "created", "last_used", "uses", "songs", "venues", "tags"), show='headings')
        self.tree.heading("username", text="Username")
        self.tree.heading("created", text="Created (Approx)")
        self.tree.heading("last_used", text="Last Used (Approx)")
        self.tree.heading("uses", text="Uses")
        self.tree.heading("songs", text="Songs")
        self.tree.heading("venues", text="Venues")
        self.tree.heading("tags", text="Tags")
        
        self.tree.column("uses", width=50)
        self.tree.column("songs", width=50)
        self.tree.column("venues", width=50)
        self.tree.column("tags", width=50)

        self.tree.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.tree.bind("<Double-1>", self.on_user_click)

    def on_user_click(self, event):
        item = self.tree.selection()[0]
        username = self.tree.item(item, "values")[0]
        self.async_handler.run(self.show_user_details(username))

    async def show_user_details(self, username):
        details = await self.db_manager.get_user_details(username)
        self.after(0, lambda: self.open_details_window(username, details))

    def open_details_window(self, username, details):
        detail_window = ctk.CTkToplevel(self)
        detail_window.title(f"Details: {username}")
        detail_window.geometry("600x500")
        detail_window.attributes("-topmost", True)

        detail_window.grid_columnconfigure((0, 1, 2), weight=1)
        detail_window.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(detail_window, text=f"User Details: {username}", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, pady=10)

        # Songs Column
        ctk.CTkLabel(detail_window, text="Songs", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="n")
        songs_box = ctk.CTkTextbox(detail_window, width=180)
        songs_box.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        songs_box.insert("1.0", "\n".join(details["songs"]) if details["songs"] else "No songs.")

        # Venues Column
        ctk.CTkLabel(detail_window, text="Venues", font=ctk.CTkFont(weight="bold")).grid(row=1, column=1, sticky="n")
        venues_box = ctk.CTkTextbox(detail_window, width=180)
        venues_box.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
        venues_box.insert("1.0", "\n".join(details["venues"]) if details["venues"] else "No venues.")

        # Tags Column
        ctk.CTkLabel(detail_window, text="Tags", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, sticky="n")
        tags_box = ctk.CTkTextbox(detail_window, width=180)
        tags_box.grid(row=2, column=2, padx=5, pady=5, sticky="nsew")
        tags_box.insert("1.0", "\n".join(details["tags"]) if details["tags"] else "No tags.")

        detail_window.grid_rowconfigure(2, weight=1)

    def setup_logs_ui(self):
        self.logs_frame.grid_columnconfigure(0, weight=1)
        self.logs_frame.grid_rowconfigure(1, weight=1)

        self.logs_title = ctk.CTkLabel(self.logs_frame, text="Application Logs", font=ctk.CTkFont(size=20, weight="bold"))
        self.logs_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.logs_textbox = ctk.CTkTextbox(self.logs_frame)
        self.logs_textbox.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

    def select_frame(self, name):
        self.current_tab = name
        # Reset buttons
        self.sidebar_button_1.configure(fg_color=("gray75", "gray25") if name != "Dashboard" else "#1f538d")
        self.sidebar_button_2.configure(fg_color=("gray75", "gray25") if name != "User Stats" else "#1f538d")
        self.sidebar_button_3.configure(fg_color=("gray75", "gray25") if name != "Logs" else "#1f538d")

        # Show selected frame
        if name == "Dashboard":
            self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.dashboard_frame.grid_forget()
        
        if name == "User Stats":
            self.user_stats_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.user_stats_frame.grid_forget()

        if name == "Logs":
            self.logs_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.logs_frame.grid_forget()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def poll_updates(self):
        """Polls for system metrics and log updates (runs on UI thread)."""
        metrics = self.monitor_engine.get_system_metrics()
        self.cpu_label.configure(text=f"CPU Usage: {metrics['cpu_percent']}%")
        self.cpu_progress.set(metrics['cpu_percent'] / 100)
        
        self.ram_label.configure(text=f"RAM Usage: {metrics['ram_percent']}%")
        self.ram_progress.set(metrics['ram_percent'] / 100)

        new_logs = self.monitor_engine.get_new_log_lines()
        if new_logs:
            self.logs_textbox.insert("end", "\n".join(new_logs) + "\n")
            self.logs_textbox.see("end")

        self.after(2000, self.poll_updates)

    def poll_db_updates(self):
        """Polls for database updates (dispatches to async thread)."""
        self.async_handler.run(self.update_db_info())
        interval = int(os.getenv("POLLING_INTERVAL_SECONDS", 5)) * 1000
        self.after(interval, self.poll_db_updates)

    async def update_db_info(self):
        # Health Check
        health = await self.db_manager.check_health()
        status_text = f"DB: {health['status']}"
        if health['status'] == "Online":
            status_text += f" ({health['latency']})"
            color = "green"
        else:
            color = "red"
        
        self.after(0, lambda: self.db_status_label.configure(text=status_text, text_color=color))

        if health['status'] == "Online":
            # Recent Performances
            perfs = await self.db_manager.get_recent_performances()
            perf_text = ""
            for p in perfs:
                perf_text += f"[{p['date']} {p['time']}] {p['username']} - {p['track_name']} @ {p['location']} (Rating: {p['rating']})\n"
            
            self.after(0, lambda: self.update_textbox(self.recent_perf_list, perf_text))

            # Upcoming Songs
            upcoming = await self.db_manager.get_upcoming_songs()
            upcoming_text = ""
            for u in upcoming:
                upcoming_text += f"{u['username']}: {u['track_name']} by {u['artist_name']} ({u['setlist_name']})\n"
            
            self.after(0, lambda: self.update_textbox(self.upcoming_songs_list, upcoming_text))

            # User Stats
            if self.current_tab == "User Stats":
                stats = await self.db_manager.get_user_stats()
                self.after(0, lambda: self.update_user_table(stats))

    def update_textbox(self, textbox, content):
        textbox.delete("1.0", "end")
        textbox.insert("1.0", content)

    def update_user_table(self, stats):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for s in stats:
            self.tree.insert("", "end", values=(
                s.get("username", ""),
                s.get("created_approx", "N/A"),
                s.get("last_used_approx", "N/A"),
                s.get("total_uses", 0),
                s.get("songs_count", 0),
                s.get("venues_count", 0),
                s.get("tags_count", 0)
            ))

if __name__ == "__main__":
    app = KaraokeMonitorApp()
    app.mainloop()
