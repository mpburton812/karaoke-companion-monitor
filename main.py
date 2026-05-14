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
        self.current_tab = "Overview"
        
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
        self.sidebar_frame.grid_rowconfigure(3, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="KARAOKE\nMONITOR", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.db_status_label = ctk.CTkLabel(self.sidebar_frame, text="DB: Checking...", text_color="gray")
        self.db_status_label.grid(row=1, column=0, padx=20, pady=5)

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Overview", command=lambda: self.select_frame("Overview"))
        self.sidebar_button_1.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Logs", command=lambda: self.select_frame("Logs"))
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

    def setup_main_frames(self):
        # Overview Frame (Combined Recent Perf + User Stats)
        self.overview_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_overview_ui()

        # Logs Frame
        self.logs_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_logs_ui()

        # Default frame
        self.select_frame("Overview")

    def setup_overview_ui(self):
        self.overview_frame.grid_columnconfigure(0, weight=1)
        self.overview_frame.grid_rowconfigure(1, weight=1) # Recent Perf section
        self.overview_frame.grid_rowconfigure(3, weight=3) # User Stats section (takes more space)

        # 1. Recent Performances Section
        self.recent_perf_label = ctk.CTkLabel(self.overview_frame, text="Recent Performances", font=ctk.CTkFont(size=16, weight="bold"))
        self.recent_perf_label.grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")

        self.recent_perf_list = ctk.CTkTextbox(self.overview_frame, height=150)
        self.recent_perf_list.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="nsew")

        # 2. User Statistics Section
        self.user_stats_label = ctk.CTkLabel(self.overview_frame, text="User Statistics (Double-click for details)", font=ctk.CTkFont(size=16, weight="bold"))
        self.user_stats_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")

        # Use a standard tkinter Treeview for the table
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        self.style.map("Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(self.overview_frame, columns=("username", "created", "last_used", "uses", "songs", "venues", "tags"), show='headings')
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

        self.tree.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="nsew")
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
        detail_window.geometry("700x600")
        detail_window.attributes("-topmost", True)

        detail_window.grid_columnconfigure((0, 1, 2), weight=1)
        detail_window.grid_rowconfigure(2, weight=1)

        # Header with user management
        header_frame = ctk.CTkFrame(detail_window, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header_frame, text=f"User Details: {username}", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=10)

        # Rename Section
        rename_frame = ctk.CTkFrame(header_frame)
        rename_frame.grid(row=0, column=1, padx=10, sticky="e")
        
        self.new_name_entry = ctk.CTkEntry(rename_frame, placeholder_text="New Username")
        self.new_name_entry.grid(row=0, column=0, padx=5, pady=5)
        
        rename_btn = ctk.CTkButton(rename_frame, text="Rename", width=60, 
                                   command=lambda: self.handle_rename(username, self.new_name_entry.get(), detail_window))
        rename_btn.grid(row=0, column=1, padx=5, pady=5)

        # Delete Section
        delete_btn = ctk.CTkButton(header_frame, text="Delete User", fg_color="red", hover_color="#8B0000", width=100,
                                   command=lambda: self.handle_delete(username, detail_window))
        delete_btn.grid(row=0, column=2, padx=10)

        # Details Content
        # Songs Column
        ctk.CTkLabel(detail_window, text="Songs", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="n")
        songs_box = ctk.CTkTextbox(detail_window, width=220)
        songs_box.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        songs_box.insert("1.0", "\n".join(details["songs"]) if details["songs"] else "No songs.")

        # Venues Column
        ctk.CTkLabel(detail_window, text="Venues", font=ctk.CTkFont(weight="bold")).grid(row=1, column=1, sticky="n")
        venues_box = ctk.CTkTextbox(detail_window, width=220)
        venues_box.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
        venues_box.insert("1.0", "\n".join(details["venues"]) if details["venues"] else "No venues.")

        # Tags Column
        ctk.CTkLabel(detail_window, text="Tags", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, sticky="n")
        tags_box = ctk.CTkTextbox(detail_window, width=220)
        tags_box.grid(row=2, column=2, padx=5, pady=5, sticky="nsew")
        tags_box.insert("1.0", "\n".join(details["tags"]) if details["tags"] else "No tags.")

    def handle_rename(self, old_name, new_name, window):
        if not new_name or new_name.strip() == "":
            return
        
        if tk.messagebox.askyesno("Confirm Rename", f"Are you sure you want to rename '{old_name}' to '{new_name}'?"):
            self.async_handler.run(self.perform_rename(old_name, new_name, window))

    async def perform_rename(self, old_name, new_name, window):
        success = await self.db_manager.update_username(old_name, new_name)
        if success:
            self.after(0, lambda: window.destroy())
            self.async_handler.run(self.update_db_info())
        else:
            self.after(0, lambda: tk.messagebox.showerror("Error", "Failed to update username."))

    def handle_delete(self, username, window):
        confirmed = tk.messagebox.askyesno("Confirm Delete", f"DANGER: Are you sure you want to delete user '{username}'? This will delete ALL their songs, performances, and data forever.")
        if confirmed:
            self.async_handler.run(self.perform_delete(username, window))

    async def perform_delete(self, username, window):
        success = await self.db_manager.delete_user(username)
        if success:
            self.after(0, lambda: window.destroy())
            self.async_handler.run(self.update_db_info())
        else:
            self.after(0, lambda: tk.messagebox.showerror("Error", "Failed to delete user."))

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
        self.sidebar_button_1.configure(fg_color=("gray75", "gray25") if name != "Overview" else "#1f538d")
        self.sidebar_button_3.configure(fg_color=("gray75", "gray25") if name != "Logs" else "#1f538d")

        # Show selected frame
        if name == "Overview":
            self.overview_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.overview_frame.grid_forget()

        if name == "Logs":
            self.logs_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.logs_frame.grid_forget()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def poll_updates(self):
        """Polls for log updates (runs on UI thread)."""
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

            # User Stats
            if self.current_tab == "Overview":
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
