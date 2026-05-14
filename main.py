import os
import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any
from plyer import notification

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

        self.title("Karaoke Companion Monitor Pro")
        self.geometry("1200x800")

        # Initialize Managers
        self.db_manager = DatabaseManager()
        self.monitor_engine = MonitorEngine(os.getenv("LOG_FILE_PATH"))
        self.async_handler = AsyncHandler()

        # UI State
        self.current_tab = "Overview"
        self.user_data = [] # Cache for searching
        self.last_db_status = "Online"
        self.log_filter_error = tk.BooleanVar(value=False)
        
        # Grid layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_main_frames()
        
        # Start polling loops
        self.poll_updates()         # System/Logs (2s)
        self.poll_db_health()       # DB Health Status (10s)
        self.poll_db_data()         # DB Performance/Stats (5 mins)

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="KARAOKE\nMONITOR PRO", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.db_status_label = ctk.CTkLabel(self.sidebar_frame, text="DB: Checking...", text_color="gray")
        self.db_status_label.grid(row=1, column=0, padx=20, pady=5)

        self.refresh_btn = ctk.CTkButton(self.sidebar_frame, text="Force Refresh", fg_color="green", hover_color="#006400", command=self.force_refresh)
        self.refresh_btn.grid(row=2, column=0, padx=20, pady=5)

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Overview", command=lambda: self.select_frame("Overview"))
        self.sidebar_button_1.grid(row=3, column=0, padx=20, pady=10)

        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Insights", command=lambda: self.select_frame("Insights"))
        self.sidebar_button_2.grid(row=4, column=0, padx=20, pady=10)

        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Venues", command=lambda: self.select_frame("Venues"))
        self.sidebar_button_3.grid(row=5, column=0, padx=20, pady=10)

        self.sidebar_button_4 = ctk.CTkButton(self.sidebar_frame, text="Logs", command=lambda: self.select_frame("Logs"))
        self.sidebar_button_4.grid(row=6, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

    def setup_main_frames(self):
        self.overview_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_overview_ui()

        self.insights_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_insights_ui()

        self.venues_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_venues_ui()

        self.logs_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_logs_ui()

        self.select_frame("Overview")

    def setup_overview_ui(self):
        self.overview_frame.grid_columnconfigure(0, weight=1)
        self.overview_frame.grid_rowconfigure(1, weight=1)
        self.overview_frame.grid_rowconfigure(4, weight=3)

        # 1. Recent Performances
        ctk.CTkLabel(self.overview_frame, text="Recent Performances", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")
        self.recent_perf_list = ctk.CTkTextbox(self.overview_frame, height=150)
        self.recent_perf_list.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="nsew")

        # 2. User Statistics with Search
        search_frame = ctk.CTkFrame(self.overview_frame, fg_color="transparent")
        search_frame.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(search_frame, text="User Statistics (Double-click for details)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search users...")
        self.search_entry.grid(row=0, column=1, padx=10, sticky="e")
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.tree = ttk.Treeview(self.overview_frame, columns=("username", "created", "last_used", "uses", "songs", "venues", "tags"), show='headings')
        # ... (Treeview headings/columns logic - same as before) ...
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=100)
        
        self.tree.grid(row=4, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.tree.bind("<Double-1>", self.on_user_click)

    def setup_insights_ui(self):
        self.insights_frame.grid_columnconfigure((0, 1), weight=1)
        self.insights_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.insights_frame, text="Popularity & Usage Insights", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, columnspan=2, pady=20)

        self.top_songs_box = ctk.CTkTextbox(self.insights_frame)
        self.top_songs_box.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.top_artists_box = ctk.CTkTextbox(self.insights_frame)
        self.top_artists_box.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")

        self.usage_patterns_box = ctk.CTkTextbox(self.insights_frame, height=150)
        self.usage_patterns_box.grid(row=2, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")

    def setup_venues_ui(self):
        self.venues_frame.grid_columnconfigure(0, weight=1)
        self.venues_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.venues_frame, text="Venue Activity", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=20)
        
        self.venue_tree = ttk.Treeview(self.venues_frame, columns=("location", "perf_count", "unique_users"), show='headings')
        self.venue_tree.heading("location", text="Venue Name")
        self.venue_tree.heading("perf_count", text="Total Performances")
        self.venue_tree.heading("unique_users", text="Unique Performers")
        self.venue_tree.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

    def setup_logs_ui(self):
        self.logs_frame.grid_columnconfigure(0, weight=1)
        self.logs_frame.grid_rowconfigure(2, weight=1)

        log_header = ctk.CTkFrame(self.logs_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        ctk.CTkLabel(log_header, text="Application Logs", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w")
        
        self.error_filter_toggle = ctk.CTkCheckBox(log_header, text="Only Errors", variable=self.log_filter_error)
        self.error_filter_toggle.grid(row=0, column=1, padx=20, sticky="e")

        self.logs_textbox = ctk.CTkTextbox(self.logs_frame)
        self.logs_textbox.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def select_frame(self, name):
        self.current_tab = name
        btns = [self.sidebar_button_1, self.sidebar_button_2, self.sidebar_button_3, self.sidebar_button_4]
        names = ["Overview", "Insights", "Venues", "Logs"]
        for b, n in zip(btns, names):
            b.configure(fg_color=("gray75", "gray25") if name != n else "#1f538d")

        for frame, f_name in zip([self.overview_frame, self.insights_frame, self.venues_frame, self.logs_frame], names):
            if name == f_name: frame.grid(row=0, column=1, sticky="nsew")
            else: frame.grid_forget()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def on_search(self, event=None):
        query = self.search_entry.get().lower()
        filtered = [u for u in self.user_data if query in u.get("username", "").lower()]
        self.update_user_table(filtered)

    def force_refresh(self):
        self.async_handler.run(self.update_db_info())
        self.async_handler.run(self.update_insights())

    def poll_updates(self):
        new_logs = self.monitor_engine.get_new_log_lines()
        if new_logs:
            for line in new_logs:
                if self.log_filter_error.get() and "error" not in line.lower() and "500" not in line:
                    continue
                self.logs_textbox.insert("end", line + "\n")
                if "error" in line.lower() or "failed" in line.lower():
                    self.send_notification("Log Alert", f"Potential error detected: {line[:50]}...")
            self.logs_textbox.see("end")
        self.after(2000, self.poll_updates)

    def poll_db_health(self):
        self.async_handler.run(self.update_db_health())
        self.after(10000, self.poll_db_health)

    def poll_db_data(self):
        self.async_handler.run(self.update_db_info())
        self.async_handler.run(self.update_insights())
        self.after(300000, self.poll_db_data)

    async def update_db_health(self):
        health = await self.db_manager.check_health()
        status = health['status']
        if status != self.last_db_status:
            self.send_notification("DB Status Change", f"Database is now {status}")
            self.last_db_status = status
        
        color = "green" if status == "Online" else "red"
        status_text = f"DB: {status} ({health.get('latency', 'N/A')})"
        self.after(0, lambda: self.db_status_label.configure(text=status_text, text_color=color))

    async def update_db_info(self):
        if self.last_db_status != "Online": return
        
        perfs = await self.db_manager.get_recent_performances()
        perf_text = "\n".join([f"[{p['date']} {p['time']}] {p['username']} - {p['track_name']} @ {p['location']}" for p in perfs])
        self.after(0, lambda: self.update_textbox(self.recent_perf_list, perf_text))

        self.user_data = await self.db_manager.get_user_stats()
        self.after(0, lambda: self.on_search()) # Re-apply search filter

    async def update_insights(self):
        if self.last_db_status != "Online": return
        
        songs = await self.db_manager.get_top_songs()
        song_text = "TOP SONGS\n" + "\n".join([f"{s['count']}x: {s['track_name']}" for s in songs])
        
        artists = await self.db_manager.get_top_artists()
        artist_text = "TOP ARTISTS\n" + "\n".join([f"{a['count']}x: {a['artist_name']}" for a in artists])
        
        patterns = await self.db_manager.get_usage_patterns()
        pattern_text = "WEEKLY USAGE\n" + "\n".join([f"{p['day']}: {p['count']} perfs" for p in patterns])

        venues = await self.db_manager.get_venue_stats()
        
        self.after(0, lambda: self.update_textbox(self.top_songs_box, song_text))
        self.after(0, lambda: self.update_textbox(self.top_artists_box, artist_text))
        self.after(0, lambda: self.update_textbox(self.usage_patterns_box, pattern_text))
        self.after(0, lambda: self.update_venue_table(venues))

    def update_venue_table(self, venues):
        for item in self.venue_tree.get_children(): self.venue_tree.delete(item)
        for v in venues: self.venue_tree.insert("", "end", values=(v['location'], v['perf_count'], v['unique_users']))

    def send_notification(self, title, message):
        try: notification.notify(title=title, message=message, app_name="Karaoke Monitor", timeout=5)
        except: pass

    # ... (on_user_click, show_user_details, open_details_window, update_textbox, update_user_table, etc. - mostly same) ...
    def on_user_click(self, event):
        selection = self.tree.selection()
        if not selection: return
        item = selection[0]
        username = self.tree.item(item, "values")[0]
        self.async_handler.run(self.show_user_details(username))

    async def show_user_details(self, username):
        details = await self.db_manager.get_user_details(username)
        self.after(0, lambda: self.open_details_window(username, details))

    def open_details_window(self, username, details):
        detail_window = ctk.CTkToplevel(self)
        detail_window.title(f"Details: {username}")
        detail_window.geometry("700x600")
        detail_window.attributes("-topmost", True)
        detail_window.grid_columnconfigure((0, 1, 2), weight=1)
        detail_window.grid_rowconfigure(2, weight=1)
        header_frame = ctk.CTkFrame(detail_window, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header_frame, text=f"User Details: {username}", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=10)
        rename_frame = ctk.CTkFrame(header_frame)
        rename_frame.grid(row=0, column=1, padx=10, sticky="e")
        self.new_name_entry = ctk.CTkEntry(rename_frame, placeholder_text="New Username")
        self.new_name_entry.grid(row=0, column=0, padx=5, pady=5)
        rename_btn = ctk.CTkButton(rename_frame, text="Rename", width=60, command=lambda: self.handle_rename(username, self.new_name_entry.get(), detail_window))
        rename_btn.grid(row=0, column=1, padx=5, pady=5)
        delete_btn = ctk.CTkButton(header_frame, text="Delete User", fg_color="red", hover_color="#8B0000", width=100, command=lambda: self.handle_delete(username, detail_window))
        delete_btn.grid(row=0, column=2, padx=10)
        cols = ["Songs", "Venues", "Tags"]
        keys = ["songs", "venues", "tags"]
        for i, (col, key) in enumerate(zip(cols, keys)):
            ctk.CTkLabel(detail_window, text=col, font=ctk.CTkFont(weight="bold")).grid(row=1, column=i, sticky="n")
            box = ctk.CTkTextbox(detail_window, width=220)
            box.grid(row=2, column=i, padx=5, pady=5, sticky="nsew")
            box.insert("1.0", "\n".join(details[key]) if details[key] else f"No {key}.")

    def handle_rename(self, old_name, new_name, window):
        if not new_name or new_name.strip() == "": return
        if messagebox.askyesno("Confirm Rename", f"Rename '{old_name}' to '{new_name}'?"):
            self.async_handler.run(self.perform_rename(old_name, new_name, window))

    async def perform_rename(self, old_name, new_name, window):
        if await self.db_manager.update_username(old_name, new_name):
            self.after(0, lambda: window.destroy())
            self.async_handler.run(self.update_db_info())
        else: self.after(0, lambda: messagebox.showerror("Error", "Failed to update username."))

    def handle_delete(self, username, window):
        if messagebox.askyesno("Confirm Delete", f"DANGER: Delete user '{username}' and ALL their data?"):
            self.async_handler.run(self.perform_delete(username, window))

    async def perform_delete(self, username, window):
        if await self.db_manager.delete_user(username):
            self.after(0, lambda: window.destroy())
            self.async_handler.run(self.update_db_info())
        else: self.after(0, lambda: messagebox.showerror("Error", "Failed to delete user."))

    def update_textbox(self, textbox, content):
        textbox.delete("1.0", "end")
        textbox.insert("1.0", content)

    def update_user_table(self, stats):
        for item in self.tree.get_children(): self.tree.delete(item)
        for s in stats:
            self.tree.insert("", "end", values=(
                s.get("username", ""), s.get("created_approx", "N/A"), s.get("last_used_approx", "N/A"),
                s.get("total_uses", 0), s.get("songs_count", 0), s.get("venues_count", 0), s.get("tags_count", 0)
            ))

if __name__ == "__main__":
    app = KaraokeMonitorApp()
    app.mainloop()


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
