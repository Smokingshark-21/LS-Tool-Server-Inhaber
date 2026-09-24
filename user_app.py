import os
import sys
import json
import ftplib
import time
import threading
import subprocess
import shutil
import re
import urllib.request
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone
from PIL import Image, ImageTk

class LS25UserApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.CURRENT_VERSION = "1.1.0"

        self.title("Landwirtschafts-Simulator | Player Hub")
        self.geometry("1020x1380")
        self.minsize(900, 900)

        app_data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'LS25PlayerHub')
        os.makedirs(app_data_dir, exist_ok=True)
        
        self.slideshow_dir = os.path.join(app_data_dir, "slideshow")
        os.makedirs(self.slideshow_dir, exist_ok=True)

        self.local_config_filename = os.path.join(app_data_dir, "ls25_config.json")
        self.user_prefs_filename = os.path.join(app_data_dir, "ls25_user_prefs.json")

        self.slide_authors = {}
        self.is_closing = False
        self.current_photo = None

        self.set_window_icon()

        self.BG_DARK = "#0d1117"        
        self.BG_CARD = "#161b22"        
        self.BG_CARD_ALT = "#21262d"    
        self.ACCENT_GREEN = "#238636"   
        self.ACCENT_AMBER = "#d29922"   
        self.ACCENT_BLUE = "#58a6ff"    
        self.ACCENT_RED = "#da3633"     
        self.TEXT_MAIN = "#c9d1d9"      
        self.TEXT_MUTED = "#8b949e"     

        self.configure(bg=self.BG_DARK)

        self.config_data = self.load_local_config()
        self.user_prefs = self.load_user_prefs()

        self.setup_styles()

        if not self.user_prefs.get("setup_completed", False) or not self.user_prefs.get("username", "").strip() or not self.config_data.get("ftp_host"):
            self.withdraw()
            self.ask_setup_modal()
        else:
            self.create_widgets()
            self.check_for_updates_and_sync()
            self.start_auto_refresh_timer()
            self.start_slideshow_timer()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_window_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(os.path.abspath(sys.executable))
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            for filename in ["logo.ico", "logo.png", "logo.jpg", "content-removebg-preview.jpg"]:
                full_path = os.path.join(base_path, filename)
                if os.path.exists(full_path):
                    if filename.endswith(".ico"):
                        self.iconbitmap(full_path)
                    else:
                        img = Image.open(full_path)
                        self.icon_image = ImageTk.PhotoImage(img)
                        self.iconphoto(True, self.icon_image)
                    return
        except Exception:
            pass

    def get_public_ip(self):
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=2) as resp:
                return resp.read().decode("utf-8").strip()
        except Exception:
            return "unknown"

    def get_default_config(self):
        return {
            "announcement": "Willkommen auf dem LS25 Community Server!",
            "webstats_url": "",
            "ftp_host": "",
            "ftp_port": 21,
            "ftp_user": "",
            "ftp_pass": "",
            "ftp_mods_path": "/mods",
            "ftp_config_remote_path": "/Launcher/ls25_config.json",
            "discord_bot_token": "",
            "discord_channel_id": "",
            "panel_users_history": [],
            "banned_panel_usernames": [],
            "banned_panel_ips": [],
            "banned_names": [],
            "banned_ips": []
        }

    def load_local_config(self):
        cfg = self.get_default_config()
        if os.path.exists(self.local_config_filename):
            try:
                with open(self.local_config_filename, "r", encoding="utf-8") as f:
                    cfg.update(json.load(f))
            except Exception:
                pass
        return cfg

    def load_user_prefs(self):
        base_game_dir = os.path.expanduser("~/Documents/My Games/FarmingSimulator2025")
        default_prefs = {
            "username": "",
            "name_locked": False,
            "game_path": "",
            "mod_path": os.path.join(base_game_dir, "mods"),
            "shader_cache_path": os.path.join(base_game_dir, "shader_cache"),
            "jim_cache_path": os.path.join(base_game_dir, "jim_cache"),
            "setup_completed": False,
            "launcher_mtime": 0
        }
        if os.path.exists(self.user_prefs_filename):
            try:
                with open(self.user_prefs_filename, "r", encoding="utf-8") as f:
                    default_prefs.update(json.load(f))
            except Exception:
                pass
        return default_prefs

    def save_user_prefs(self):
        try:
            with open(self.user_prefs_filename, "w", encoding="utf-8") as f:
                json.dump(self.user_prefs, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Einstellungen: {e}")

    def save_local_config(self):
        try:
            with open(self.local_config_filename, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der lokalen Config: {e}")

    def update_game_settings_mod_path(self):
        try:
            mod_path = self.user_prefs.get("mod_path", "").strip()
            if not mod_path:
                return

            formatted_path = mod_path.replace("\\", "/")
            games_dir = os.path.expanduser("~/Documents/My Games/FarmingSimulator2025")
            settings_path = os.path.join(games_dir, "gameSettings.xml")

            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if "<modsDirectoryOverride" in content:
                    new_content = re.sub(
                        r'<modsDirectoryOverride[^>]*>',
                        f'<modsDirectoryOverride active="true" directory="{formatted_path}"/>',
                        content
                    )
                else:
                    if "</gameSettings>" in content:
                        new_content = content.replace("</gameSettings>", f'    <modsDirectoryOverride active="true" directory="{formatted_path}"/>\n</gameSettings>')
                    else:
                        new_content = content + f'\n<modsDirectoryOverride active="true" directory="{formatted_path}"/>'

                with open(settings_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
        except Exception as e:
            print(f"Fehler beim Aktualisieren der gameSettings.xml: {e}")

    def ask_setup_modal(self):
        modal = tk.Toplevel(self)
        modal.title("Ersteinrichtung - Player Hub")
        modal.geometry("600x750")
        modal.configure(bg=self.BG_DARK)
        modal.resizable(False, False)
        modal.grab_set()

        modal.update_idletasks()
        w = modal.winfo_width()
        h = modal.winfo_height()
        x = (modal.winfo_screenwidth() // 2) - (w // 2)
        y = (modal.winfo_screenheight() // 2) - (h // 2)
        modal.geometry(f"{w}x{h}+{x}+{y}")

        canvas = tk.Canvas(modal, bg=self.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(modal, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Card.TFrame", padding=20)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        tk.Label(scrollable_frame, text="🌾 Ersteinrichtung des Player Hubs", bg=self.BG_CARD, fg=self.ACCENT_AMBER, font=("Segoe UI", 12, "bold")).pack(pady=(0, 4))
        tk.Label(scrollable_frame, text="Bitte gib deinen Spielernamen, Server- und Pfaddaten ein:", bg=self.BG_CARD, fg=self.TEXT_MAIN, font=("Segoe UI", 9)).pack(pady=(0, 12))

        # Spielername
        tk.Label(scrollable_frame, text="Spielername:", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry_name = ttk.Entry(scrollable_frame, font=("Segoe UI", 10), width=50)
        entry_name.pack(fill="x", pady=(2, 8))
        entry_name.insert(0, self.user_prefs.get("username", ""))

        # Server FTP Einstellungen
        tk.Label(scrollable_frame, text="FTP Host (Server-IP / Domain):", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry_ftphost = ttk.Entry(scrollable_frame, font=("Segoe UI", 10), width=50)
        entry_ftphost.pack(fill="x", pady=(2, 8))
        entry_ftphost.insert(0, self.config_data.get("ftp_host", ""))

        tk.Label(scrollable_frame, text="FTP Port:", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry_ftpport = ttk.Entry(scrollable_frame, font=("Segoe UI", 10), width=50)
        entry_ftpport.pack(fill="x", pady=(2, 8))
        entry_ftpport.insert(0, str(self.config_data.get("ftp_port", 21)))

        tk.Label(scrollable_frame, text="FTP Benutzer:", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry_ftpuser = ttk.Entry(scrollable_frame, font=("Segoe UI", 10), width=50)
        entry_ftpuser.pack(fill="x", pady=(2, 8))
        entry_ftpuser.insert(0, self.config_data.get("ftp_user", ""))

        tk.Label(scrollable_frame, text="FTP Passwort:", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry_ftppass = ttk.Entry(scrollable_frame, font=("Segoe UI", 10), width=50, show="*")
        entry_ftppass.pack(fill="x", pady=(2, 8))
        entry_ftppass.insert(0, self.config_data.get("ftp_pass", ""))

        tk.Label(scrollable_frame, text="Webstats XML URL (Live-Anzeige):", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry_webstats = ttk.Entry(scrollable_frame, font=("Segoe UI", 10), width=50)
        entry_webstats.pack(fill="x", pady=(2, 8))
        entry_webstats.insert(0, self.config_data.get("webstats_url", ""))

        # Pfade
        tk.Label(scrollable_frame, text="Pfad zur FarmingSimulator2025.exe:", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        game_frame = ttk.Frame(scrollable_frame, style="Card.TFrame")
        game_frame.pack(fill="x", pady=(2, 8))
        entry_game = ttk.Entry(game_frame, font=("Segoe UI", 10))
        entry_game.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry_game.insert(0, self.user_prefs.get("game_path", ""))
        def browse_game():
            fp = filedialog.askopenfilename(title="FarmingSimulator2025.exe auswählen", filetypes=[("Executable", "*.exe"), ("Alle Dateien", "*.*")], parent=modal)
            if fp:
                entry_game.delete(0, tk.END)
                entry_game.insert(0, fp)
        ttk.Button(game_frame, text="Durchsuchen", command=browse_game).pack(side="right")

        tk.Label(scrollable_frame, text="Pfad zum Mod-Ordner:", bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        mod_frame = ttk.Frame(scrollable_frame, style="Card.TFrame")
        mod_frame.pack(fill="x", pady=(2, 8))
        entry_mod = ttk.Entry(mod_frame, font=("Segoe UI", 10))
        entry_mod.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry_mod.insert(0, self.user_prefs.get("mod_path", ""))
        def browse_mod():
            folder = filedialog.askdirectory(title="Mod-Ordner auswählen", parent=modal)
            if folder:
                entry_mod.delete(0, tk.END)
                entry_mod.insert(0, folder)
        ttk.Button(mod_frame, text="Durchsuchen", command=browse_mod).pack(side="right")

        def save_and_proceed(event=None):
            name = entry_name.get().strip()
            host = entry_ftphost.get().strip()
            port_str = entry_ftpport.get().strip()
            user = entry_ftpuser.get().strip()
            pwd = entry_ftppass.get().strip()
            w_url = entry_webstats.get().strip()
            g_path = entry_game.get().strip()
            m_path = entry_mod.get().strip()

            if not name:
                messagebox.showwarning("Fehler", "Bitte gib einen gültigen Spielernamen ein!", parent=modal)
                return
            if not host:
                messagebox.showwarning("Fehler", "Bitte gib den FTP-Host des Servers ein!", parent=modal)
                return
            if not m_path:
                messagebox.showwarning("Fehler", "Bitte wähle einen gültigen Mod-Ordner aus!", parent=modal)
                return

            self.user_prefs["username"] = name
            self.user_prefs["name_locked"] = True
            self.user_prefs["game_path"] = g_path
            self.user_prefs["mod_path"] = m_path
            self.user_prefs["setup_completed"] = True
            self.save_user_prefs()
            self.update_game_settings_mod_path()

            self.config_data["ftp_host"] = host
            try:
                self.config_data["ftp_port"] = int(port_str)
            except ValueError:
                self.config_data["ftp_port"] = 21
            self.config_data["ftp_user"] = user
            self.config_data["ftp_pass"] = pwd
            self.config_data["webstats_url"] = w_url
            self.save_local_config()

            modal.destroy()
            self.deiconify()
            self.create_widgets()
            self.check_for_updates_and_sync()
            self.start_auto_refresh_timer()
            self.start_slideshow_timer()

        btn_save = ttk.Button(scrollable_frame, text="Ersteinrichtung abschließen & Starten", style="Accent.TButton", command=save_and_proceed)
        btn_save.pack(fill="x", ipady=6, pady=(15, 10))

        modal.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=self.BG_DARK)
        style.configure("Card.TFrame", background=self.BG_CARD)
        style.configure("TLabelframe", background=self.BG_CARD, foreground=self.ACCENT_AMBER, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=self.BG_CARD, foreground=self.ACCENT_AMBER, font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8, background=self.BG_CARD_ALT, foreground=self.TEXT_MAIN, borderwidth=0)
        style.map("TButton", background=[("active", "#30363d")])
        style.configure("Accent.TButton", background=self.ACCENT_GREEN, foreground="#ffffff")
        style.configure("Play.TButton", background=self.ACCENT_GREEN, foreground="#ffffff", font=("Segoe UI", 13, "bold"))
        style.map("Play.TButton", background=[("active", "#2ea043"), ("disabled", "#21262d")], foreground=[("disabled", "#c9d1d9")])
        style.configure("TEntry", fieldbackground="#0d1117", foreground=self.TEXT_MAIN, insertcolor="#ffffff", borderwidth=1, relief="solid")
        style.configure("TLabel", background=self.BG_CARD, foreground=self.TEXT_MAIN, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=self.BG_DARK, foreground=self.ACCENT_AMBER, font=("Segoe UI", 18, "bold"))
        style.configure("Treeview", background=self.BG_CARD, foreground=self.TEXT_MAIN, fieldbackground=self.BG_CARD, rowheight=28, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=self.BG_CARD_ALT, foreground=self.ACCENT_AMBER, font=("Segoe UI", 10, "bold"))

    def create_widgets(self):
        bottom_bar = ttk.Frame(self, style="TFrame", padding=(20, 5))
        bottom_bar.pack(side="bottom", fill="x")

        self.lbl_version = tk.Label(bottom_bar, text=f"Version: {self.CURRENT_VERSION}", bg=self.BG_DARK, fg=self.TEXT_MUTED, font=("Segoe UI", 9))
        self.lbl_version.pack(side="left")

        header_frame = ttk.Frame(self, style="TFrame", padding=(20, 15))
        header_frame.pack(fill="x")

        left_header = ttk.Frame(header_frame, style="TFrame")
        left_header.pack(side="left", anchor="w")

        tk.Label(left_header, text="🌾 LS25 Player Hub", bg=self.BG_DARK, fg=self.ACCENT_AMBER, font=("Segoe UI", 18, "bold")).pack(anchor="w")

        self.lbl_announcement = tk.Label(left_header, text="🔄 Lade Daten...", bg=self.BG_DARK, fg=self.ACCENT_AMBER, font=("Segoe UI", 9, "italic"))
        self.lbl_announcement.pack(anchor="w", pady=(3, 0))

        player_frame = ttk.Frame(header_frame, style="TFrame")
        player_frame.pack(side="right", anchor="n")

        tk.Label(player_frame, text="👤 Spielername:", bg=self.BG_DARK, fg=self.TEXT_MUTED, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
        
        lbl_username_val = tk.Label(player_frame, text=self.user_prefs.get("username", ""), bg=self.BG_CARD_ALT, fg=self.ACCENT_GREEN, font=("Segoe UI", 10, "bold"), padx=12, pady=4, relief="solid", bd=1)
        lbl_username_val.pack(side="left")

        play_box = ttk.Frame(self, style="TFrame", padding=(20, 5))
        play_box.pack(fill="x")

        self.btn_play = ttk.Button(play_box, text="🎮 LS25 STARTEN (Intro wird übersprungen)", style="Play.TButton", state="disabled", command=self.launch_game)
        self.btn_play.pack(fill="x", ipady=6)

        slideshow_box = ttk.Frame(self, style="TFrame", padding=(20, 2))
        slideshow_box.pack(fill="x", expand=True)
        
        self.lbl_slideshow = tk.Label(slideshow_box, bg=self.BG_CARD, bd=1, relief="solid")
        self.lbl_slideshow.pack(fill="x", expand=True)
        self.lbl_slideshow.bind("<Configure>", self.on_slideshow_resize)

        self.lbl_slide_author = tk.Label(slideshow_box, text="📌 Gepostet von: ---", bg=self.BG_DARK, fg=self.ACCENT_AMBER, font=("Segoe UI", 9, "bold"), anchor="e")
        self.lbl_slide_author.pack(fill="x", pady=(2, 0))

        status_box = ttk.LabelFrame(self, text=" 📊 Live Server Status ", padding=15)
        status_box.pack(fill="x", padx=20, pady=10)

        cards_frame = ttk.Frame(status_box, style="Card.TFrame")
        cards_frame.pack(fill="x")

        self.card_name = self.create_card(cards_frame, "SERVER NAME", "---", self.ACCENT_BLUE)
        self.card_name.pack(side="left", fill="x", expand=True, padx=5)

        self.card_map = self.create_card(cards_frame, "KARTE", "---", self.ACCENT_AMBER)
        self.card_map.pack(side="left", fill="x", expand=True, padx=5)

        self.card_players = self.create_card(cards_frame, "SPIELER", "- / -", self.ACCENT_AMBER)
        self.card_players.pack(side="left", fill="x", expand=True, padx=5)

        self.card_fps = self.create_card(cards_frame, "SERVER FPS", "---", self.ACCENT_GREEN)
        self.card_fps.pack(side="left", fill="x", expand=True, padx=5)

        sync_box = ttk.LabelFrame(self, text=" ⚙️ Pfade & Cache & Mod-Synchronisation ", padding=15)
        sync_box.pack(fill="both", expand=True, padx=20, pady=(5, 10))

        game_path_frame = ttk.Frame(sync_box, style="Card.TFrame")
        game_path_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(game_path_frame, text="Spiel-Pfad (EXE):", width=18).pack(side="left", padx=(0, 10))
        self.entry_gamepath = ttk.Entry(game_path_frame)
        self.entry_gamepath.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_gamepath.insert(0, self.user_prefs.get("game_path", ""))
        self.entry_gamepath.bind("<KeyRelease>", lambda e: self.save_user_prefs_fields())
        ttk.Button(game_path_frame, text="Durchsuchen...", command=self.browse_game_exe).pack(side="right")

        mod_path_frame = ttk.Frame(sync_box, style="Card.TFrame")
        mod_path_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(mod_path_frame, text="Mod-Ordner:", width=18).pack(side="left", padx=(0, 10))
        self.entry_modpath = ttk.Entry(mod_path_frame)
        self.entry_modpath.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_modpath.insert(0, self.user_prefs.get("mod_path", ""))
        self.entry_modpath.bind("<KeyRelease>", lambda e: self.save_user_prefs_fields())
        ttk.Button(mod_path_frame, text="Durchsuchen...", command=self.browse_mod_folder).pack(side="right")

        shader_path_frame = ttk.Frame(sync_box, style="Card.TFrame")
        shader_path_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(shader_path_frame, text="Shader-Cache:", width=18).pack(side="left", padx=(0, 10))
        self.entry_shaderpath = ttk.Entry(shader_path_frame)
        self.entry_shaderpath.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_shaderpath.insert(0, self.user_prefs.get("shader_cache_path", ""))
        self.entry_shaderpath.bind("<KeyRelease>", lambda e: self.save_user_prefs_fields())
        def browse_shader_main():
            folder = filedialog.askdirectory(title="Shader-Cache Ordner auswählen")
            if folder:
                self.entry_shaderpath.delete(0, tk.END)
                self.entry_shaderpath.insert(0, folder)
                self.save_user_prefs_fields()
        ttk.Button(shader_path_frame, text="Durchsuchen...", command=browse_shader_main).pack(side="right")

        jim_path_frame = ttk.Frame(sync_box, style="Card.TFrame")
        jim_path_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(jim_path_frame, text="Jim-Cache:", width=18).pack(side="left", padx=(0, 10))
        self.entry_jimpath = ttk.Entry(jim_path_frame)
        self.entry_jimpath.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_jimpath.insert(0, self.user_prefs.get("jim_cache_path", ""))
        self.entry_jimpath.bind("<KeyRelease>", lambda e: self.save_user_prefs_fields())
        def browse_jim_main():
            folder = filedialog.askdirectory(title="Jim-Cache Ordner auswählen")
            if folder:
                self.entry_jimpath.delete(0, tk.END)
                self.entry_jimpath.insert(0, folder)
                self.save_user_prefs_fields()
        ttk.Button(jim_path_frame, text="Durchsuchen...", command=browse_jim_main).pack(side="right")

        btn_clear_cache = ttk.Button(sync_box, text="🧹 Shader- & Jim-Cache bereinigen", command=self.clear_game_cache)
        btn_clear_cache.pack(fill="x", pady=(0, 12))

        columns = ("name", "status")
        self.tree_mods = ttk.Treeview(sync_box, columns=columns, show="headings", selectmode="browse")
        self.tree_mods.heading("name", text="Mod Dateiname")
        self.tree_mods.heading("status", text="Status & Versions-Abgleich")
        self.tree_mods.column("name", width=520, minwidth=250, stretch=True)
        self.tree_mods.column("status", width=240, minwidth=140, stretch=False)
        self.tree_mods.pack(fill="both", expand=True)

        self.slide_files = []
        self.current_slide_index = 0
        self._last_slide_width = 0
        self.load_slideshow_images()

    def start_auto_refresh_timer(self):
        def periodic_refresh():
            if not self.is_closing:
                self.check_for_updates_and_sync()
                self.after(30000, periodic_refresh)
        self.after(30000, periodic_refresh)

    def start_slideshow_timer(self):
        def rotate_slides():
            if not self.is_closing:
                if self.slide_files:
                    self.current_slide_index = (self.current_slide_index + 1) % len(self.slide_files)
                    self.show_current_slide()
                self.after(5000, rotate_slides)
        self.after(5000, rotate_slides)

    def load_slideshow_images(self):
        try:
            self.slide_files.clear()
            if os.path.exists(self.slideshow_dir):
                valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
                files = [f for f in os.listdir(self.slideshow_dir) if f.lower().endswith(valid_exts)]
                self.slide_files = sorted(files)
            
            if self.slide_files:
                self.show_current_slide()
            else:
                self.lbl_slideshow.config(image="", text="🖼️ Keine Bilder gefunden oder Token/Channel-ID prüfen!", fg=self.TEXT_MUTED, font=("Segoe UI", 9))
                self.lbl_slide_author.config(text="")
        except Exception:
            pass

    def show_current_slide(self):
        if not self.slide_files or self.is_closing:
            return
        
        filename = self.slide_files[self.current_slide_index]
        file_path = os.path.join(self.slideshow_dir, filename)
        if not os.path.exists(file_path):
            return

        try:
            raw_img = Image.open(file_path).convert("RGB")
        except Exception:
            return

        author = self.slide_authors.get(filename, "Unbekannt")
        self.lbl_slide_author.config(text=f"📌 Gepostet von: {author}")

        w = self.lbl_slideshow.winfo_width()
        if w < 100:
            w = 960  
        h = 380

        img_w, img_h = raw_img.size
        img_ratio = img_w / img_h
        target_ratio = w / h

        if img_ratio > target_ratio:
            new_w = w
            new_h = int(w / img_ratio)
        else:
            new_h = h
            new_w = int(h * img_ratio)

        resized_img = raw_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        bg = Image.new("RGB", (w, h), self.BG_CARD)
        paste_x = (w - new_w) // 2
        paste_y = (h - new_h) // 2
        bg.paste(resized_img, (paste_x, paste_y))

        self.current_photo = ImageTk.PhotoImage(bg)
        self.lbl_slideshow.config(image=self.current_photo, text="")

    def on_slideshow_resize(self, event):
        if event.width > 100 and event.width != self._last_slide_width:
            self._last_slide_width = event.width
            if self.slide_files:
                self.show_current_slide()

    def fetch_images_from_discord(self):
        if self.is_closing:
            return
        token = self.config_data.get("discord_bot_token", "")
        channel_id = self.config_data.get("discord_channel_id", "")
        if not token or not channel_id:
            return

        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=25"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bot {token}",
                "User-Agent": "DiscordBot (https://github.com/discord/discord-api-docs, 10)"
            })
            
            with urllib.request.urlopen(req, timeout=6) as resp:
                messages = json.loads(resp.read().decode("utf-8"))
                for msg in messages:
                    if self.is_closing:
                        break
                    author_obj = msg.get("author", {})
                    member_obj = msg.get("member", {})
                    
                    nick = member_obj.get("nick") if member_obj else None
                    global_name = author_obj.get("global_name")
                    username = author_obj.get("username", "Unbekannt")
                    author_name = nick or global_name or username
                    
                    for att in msg.get("attachments", []):
                        att_url = att.get("url", "")
                        filename = att.get("filename", "")
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            local_path = os.path.join(self.slideshow_dir, filename)
                            self.slide_authors[filename] = author_name
                            if not os.path.exists(local_path):
                                try:
                                    img_req = urllib.request.Request(att_url, headers={'User-Agent': 'DiscordBot'})
                                    with urllib.request.urlopen(img_req, timeout=5) as img_resp:
                                        with open(local_path, "wb") as f_img:
                                            f_img.write(img_resp.read())
                                except Exception:
                                    pass

            if not self.is_closing:
                self.after(0, self.load_slideshow_images)
        except Exception as e:
            print(f"Discord API Fehler: {e}")

    def save_user_prefs_fields(self):
        try:
            self.user_prefs["game_path"] = self.entry_gamepath.get().strip()
            self.user_prefs["mod_path"] = self.entry_modpath.get().strip()
            self.user_prefs["shader_cache_path"] = self.entry_shaderpath.get().strip()
            self.user_prefs["jim_cache_path"] = self.entry_jimpath.get().strip()
            self.save_user_prefs()
            self.update_game_settings_mod_path()
        except Exception:
            pass

    def create_card(self, parent, title, initial_val, border_color):
        card_outer = tk.Frame(parent, bg=border_color, bd=1)
        card_inner = tk.Frame(card_outer, bg=self.BG_CARD_ALT)
        card_inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(card_inner, text=title, bg=self.BG_CARD_ALT, fg=self.TEXT_MUTED, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        lbl_val = tk.Label(card_inner, text=initial_val, bg=self.BG_CARD_ALT, fg=self.TEXT_MAIN, font=("Segoe UI", 13, "bold"), anchor="w")
        lbl_val.pack(fill="x", padx=12, pady=(4, 12))
        card_outer.lbl_val = lbl_val
        return card_outer

    def clear_game_cache(self):
        try:
            shader_path = self.entry_shaderpath.get().strip()
            jim_path = self.entry_jimpath.get().strip()
            
            cleaned_folders = []
            errors = []

            for path, name in [(shader_path, "Shader-Cache"), (jim_path, "Jim-Cache")]:
                if path:
                    if os.path.exists(path):
                        try:
                            item_count = 0
                            for item in os.listdir(path):
                                item_path = os.path.join(path, item)
                                try:
                                    if os.path.isfile(item_path) or os.path.islink(item_path):
                                        os.unlink(item_path)
                                        item_count += 1
                                    elif os.path.isdir(item_path):
                                        shutil.rmtree(item_path)
                                        item_count += 1
                                except Exception:
                                    pass
                            cleaned_folders.append(f"{name} ({item_count} Elemente bereinigt)")
                        except Exception as e:
                            errors.append(f"{name}: {e}")
                    else:
                        errors.append(f"{name}: Ordnerpfad existiert nicht.")

            msg = ""
            if cleaned_folders:
                msg += "Erfolgreich geleert:\n" + "\n".join(cleaned_folders)
            if errors:
                if msg:
                    msg += "\n\n"
                msg += "Hinweise:\n" + "\n".join(errors)

            if msg:
                messagebox.showinfo("Cache Bereinigung", msg)
            else:
                messagebox.showwarning("Hinweis", "Es wurden keine Cache-Pfade angegeben.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Unerwarteter Fehler: {e}")

    def get_remote_mtime(self, ftp, filename):
        try:
            resp = ftp.sendcmd(f"MDTM {filename}")
            if resp.startswith("213"):
                return datetime.strptime(resp[4:].strip()[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            pass
        return 0

    def check_launcher_auto_update(self, ftp):
        try:
            ftp.cwd("/")
            remote_launcher_path = "/Launcher/user_app.exe"
            remote_mtime = self.get_remote_mtime(ftp, remote_launcher_path)
            local_mtime = self.user_prefs.get("launcher_mtime", 0)

            if remote_mtime > 0 and remote_mtime > local_mtime:
                self.after(0, lambda: self.lbl_announcement.config(text="🚀 Launcher-Update gefunden! Lade neue Version...", fg=self.ACCENT_BLUE))

                current_exe = sys.executable if getattr(sys, 'frozen', False) else "user_app.exe"
                exe_dir = os.path.dirname(os.path.abspath(current_exe))
                exe_name = os.path.basename(current_exe)

                new_exe_name = "user_app_new.exe"
                new_exe_path = os.path.join(exe_dir, new_exe_name)
                target_exe_path = os.path.join(exe_dir, exe_name)
                old_exe_path = os.path.join(exe_dir, "user_app_old.exe")

                with open(new_exe_path, "wb") as f_out:
                    ftp.retrbinary(f"RETR {remote_launcher_path}", f_out.write)

                self.user_prefs["launcher_mtime"] = remote_mtime
                self.save_user_prefs()

                bat_path = os.path.join(exe_dir, "update_launcher.bat")
                with open(bat_path, "w", encoding="utf-8") as f_bat:
                    f_bat.write(f"""@echo off
chcp 65001 > nul
echo Wende Update an und starte neu...

:waitloop
tasklist /fi "imagename eq {exe_name}" 2>nul | find /i "{exe_name}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto waitloop
)

if exist "{old_exe_path}" del "{old_exe_path}" /f /q
ren "{target_exe_path}" "user_app_old.exe"
move /y "{new_exe_path}" "{target_exe_path}"
start "" "{target_exe_path}"
timeout /t 2 /nobreak > nul
if exist "{old_exe_path}" del "{old_exe_path}" /f /q
del "%~f0"
""")

                self.after(0, lambda: messagebox.showinfo("Update verfügbar", "Ein neues Update für das Player Hub wurde heruntergeladen!\nDas Programm schließt sich und startet automatisch neu."))
                
                subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=0x08000000)
                self.on_close()
        except Exception as e:
            print(f"Auto-Update Fehler: {e}")

    def update_mod_status_in_tree(self, mod_name, status_text):
        for item in self.tree_mods.get_children():
            vals = self.tree_mods.item(item, "values")
            if vals and vals[0] == mod_name:
                self.tree_mods.item(item, values=(mod_name, status_text))
                break

    def check_for_updates_and_sync(self):
        def worker():
            if self.is_closing:
                return
            ftp_host = self.config_data.get("ftp_host", "")
            ftp_port = int(self.config_data.get("ftp_port", 21))
            ftp_user = self.config_data.get("ftp_user", "")
            ftp_pass = self.config_data.get("ftp_pass", "")
            current_user = self.user_prefs.get("username", "")
            current_ip = self.get_public_ip()

            if not ftp_host:
                return

            try:
                ftp = ftplib.FTP()
                ftp.set_pasv(True)
                ftp.connect(ftp_host, ftp_port, timeout=6)
                ftp.login(ftp_user, ftp_pass)

                if self.is_closing:
                    ftp.quit()
                    return

                self.check_launcher_auto_update(ftp)

                try:
                    ftp.cwd("Launcher")
                except Exception:
                    try:
                        ftp.cwd("/Launcher")
                    except Exception:
                        pass

                with open(self.local_config_filename, "wb") as f_out:
                    try:
                        ftp.retrbinary("RETR ls25_config.json", f_out.write)
                    except Exception:
                        pass
                
                if os.path.exists(self.local_config_filename):
                    try:
                        with open(self.local_config_filename, "r", encoding="utf-8") as f:
                            self.config_data.update(json.load(f))
                    except Exception:
                        pass

                threading.Thread(target=self.fetch_images_from_discord, daemon=True).start()

                banned_panel_users = self.config_data.get("banned_panel_usernames", [])
                banned_panel_ips = self.config_data.get("banned_panel_ips", [])

                if current_user in banned_panel_users or current_ip in banned_panel_ips:
                    self.after(0, lambda: messagebox.showerror("Zugriff gesperrt", "Du wurdest gesperrt. Melde dich per Ticket auf dem Discord."))
                    self.after(0, self.on_close)
                    return

                panel_history = self.config_data.get("panel_users_history", [])
                entry_exists = any(isinstance(e, dict) and e.get("username") == current_user and e.get("ip") == current_ip for e in panel_history)

                if not entry_exists and current_user:
                    panel_history.append({"username": current_user, "ip": current_ip})
                    self.config_data["panel_users_history"] = panel_history
                    
                    try:
                        with open(self.local_config_filename, "w", encoding="utf-8") as f:
                            json.dump(self.config_data, f, indent=4, ensure_ascii=False)
                        with open(self.local_config_filename, "rb") as f:
                            ftp.storbinary("STOR ls25_config.json", f)
                    except Exception:
                        pass

                server_files = []
                try:
                    ftp.cwd("/")
                    mods_path = self.config_data.get("ftp_mods_path", "/mods")
                    ftp.cwd(mods_path)
                    server_files = ftp.nlst()
                except Exception:
                    try:
                        ftp.cwd("/mods")
                        server_files = ftp.nlst()
                    except Exception:
                        server_files = []
                
                local_dir = self.entry_modpath.get().strip()
                if os.path.exists(local_dir):
                    local_files = [f for f in os.listdir(local_dir) if f.lower().endswith('.zip')]
                    server_files_set = {f for f in server_files if f.lower().endswith('.zip')}

                    for mod in server_files_set:
                        if self.is_closing:
                            break
                        local_path = os.path.join(local_dir, mod)
                        download_needed = False

                        if not os.path.exists(local_path):
                            download_needed = True
                        else:
                            remote_time = self.get_remote_mtime(ftp, mod)
                            local_time = os.path.getmtime(local_path)
                            
                            if remote_time > 0:
                                if remote_time > local_time + 2:
                                    download_needed = True
                            else:
                                try:
                                    remote_size = ftp.size(mod)
                                    local_size = os.path.getsize(local_path)
                                    if remote_size != local_size:
                                        download_needed = True
                                except Exception:
                                    pass

                        if download_needed:
                            try:
                                self.after(0, lambda: self.btn_play.config(state="disabled"))
                                try:
                                    total_size = ftp.size(mod)
                                except Exception:
                                    total_size = 0

                                start_time = time.time()
                                downloaded_bytes = [0]

                                def download_callback(block):
                                    f_dl.write(block)
                                    downloaded_bytes[0] += len(block)
                                    elapsed = time.time() - start_time
                                    if elapsed > 0 and total_size > 0:
                                        speed = downloaded_bytes[0] / elapsed
                                        if speed > 0:
                                            remaining_secs = int((total_size - downloaded_bytes[0]) / speed)
                                            percent = int((downloaded_bytes[0] / total_size) * 100)
                                            btn_msg = f"⏳ Lade Mod: {percent}% (Noch ca. {remaining_secs}s)"
                                            tree_msg = f"⏳ Herunterladen... ({percent}%)"
                                        else:
                                            btn_msg, tree_msg = "⏳ Lade...", "⏳ Herunterladen..."
                                    else:
                                        kb = downloaded_bytes[0] // 1024
                                        btn_msg, tree_msg = f"⏳ Lade... ({kb} KB)", f"⏳ ({kb} KB)"

                                    self.after(0, lambda m=mod, s=tree_msg: self.update_mod_status_in_tree(m, s))
                                    self.after(0, lambda b=btn_msg: self.btn_play.config(text=b))

                                with open(local_path, "wb") as f_dl:
                                    ftp.retrbinary(f"RETR {mod}", download_callback)
                            except Exception as dl_err:
                                print(f"Download-Fehler: {dl_err}")

                ftp.quit()
            except Exception as e:
                print(f"Hintergrund-Sync Fehler: {e}")
                return

            if not self.is_closing:
                ann = self.config_data.get("announcement", "")
                if ann:
                    self.after(0, lambda: self.lbl_announcement.config(text=f"📢 {ann}", fg=self.TEXT_MAIN))

                self.refresh_server_status_internal()
                self.refresh_mods_table()

        threading.Thread(target=worker, daemon=True).start()

    def refresh_server_status_internal(self):
        if self.is_closing:
            return
        url = self.config_data.get("webstats_url", "")
        if not url:
            return
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)

                s_name = root.attrib.get('name', 'Community Server')
                map_name = root.attrib.get('mapName', 'Standard')
                slots = root.attrib.get('slots', '0')
                num_players = sum(1 for s in root.findall('Slots') for p in s.findall('Player') if p.attrib.get('isUsed') == 'true')
                
                if not self.is_closing:
                    self.after(0, lambda: self.update_cards(s_name, map_name, f"{num_players} / {slots}", "60 FPS"))
        except Exception:
            pass

    def update_cards(self, name, map_n, players, fps):
        if not self.is_closing:
            self.card_name.lbl_val.config(text=name)
            self.card_map.lbl_val.config(text=map_n)
            self.card_players.lbl_val.config(text=players)
            self.card_fps.lbl_val.config(text=fps)

    def refresh_mods_table(self):
        if self.is_closing:
            return
        local_dir = self.entry_modpath.get().strip()
        if not os.path.exists(local_dir):
            return

        try:
            local_files = [f for f in os.listdir(local_dir) if f.lower().endswith('.zip')]
        except Exception:
            local_files = []

        ftp_host = self.config_data.get("ftp_host", "")
        ftp_port = int(self.config_data.get("ftp_port", 21))
        ftp_user = self.config_data.get("ftp_user", "")
        ftp_pass = self.config_data.get("ftp_pass", "")
        ftp_mods_path = self.config_data.get("ftp_mods_path", "/mods")

        server_files_set = set()
        remote_times = {}
        try:
            ftp = ftplib.FTP()
            ftp.set_pasv(True)
            ftp.connect(ftp_host, ftp_port, timeout=5)
            ftp.login(ftp_user, ftp_pass)
            try:
                ftp.cwd("/")
                ftp.cwd(ftp_mods_path)
                server_files_set = {f for f in ftp.nlst() if f.lower().endswith('.zip')}
                for mod in server_files_set:
                    remote_times[mod] = self.get_remote_mtime(ftp, mod)
            except Exception:
                try:
                    ftp.cwd("/mods")
                    server_files_set = {f for f in ftp.nlst() if f.lower().endswith('.zip')}
                    for mod in server_files_set:
                        remote_times[mod] = self.get_remote_mtime(ftp, mod)
                except Exception:
                    pass
            ftp.quit()
        except Exception:
            pass

        all_mods = sorted(list(set(local_files) | server_files_set))
        table_data = []

        for mod in all_mods:
            is_local = mod in local_files
            is_server = mod in server_files_set

            if is_local and is_server:
                local_path = os.path.join(local_dir, mod)
                local_time = os.path.getmtime(local_path)
                remote_time = remote_times.get(mod, 0)
                status = "🔄 Update verfügbar" if remote_time > 0 and remote_time > local_time + 2 else "✅ Synchron & Aktuell"
            elif is_server and not is_local:
                status = "📥 Automatisch heruntergeladen"
            elif is_local and not is_server:
                status = "📤 Nur lokal vorhanden"
            else:
                status = "Unbekannt"

            table_data.append((mod, status))

        def update_ui():
            if not self.is_closing:
                for item in self.tree_mods.get_children():
                    self.tree_mods.delete(item)
                for mod, status in table_data:
                    self.tree_mods.insert("", "end", values=(mod, status))

                self.btn_play.config(state="normal", text="🎮 LS25 STARTEN (Intro wird übersprungen)")
                self.lbl_announcement.config(text=f"✅ Bereit zum Start (Version {self.CURRENT_VERSION})", fg=self.ACCENT_GREEN)

        if not self.is_closing:
            self.after(0, update_ui)

    def browse_game_exe(self):
        file_path = filedialog.askopenfilename(title="FarmingSimulator2025.exe auswählen", filetypes=[("Executable", "*.exe")])
        if file_path:
            self.entry_gamepath.delete(0, tk.END)
            self.entry_gamepath.insert(0, file_path)
            self.save_user_prefs_fields()

    def browse_mod_folder(self):
        folder = filedialog.askdirectory(title="Mod-Ordner auswählen")
        if folder:
            self.entry_modpath.delete(0, tk.END)
            self.entry_modpath.insert(0, folder)
            self.save_user_prefs_fields()
            self.refresh_mods_table()

    def launch_game(self):
        self.save_user_prefs_fields()
        self.update_game_settings_mod_path()
        game_path = self.entry_gamepath.get().strip()
        mod_path = self.user_prefs.get("mod_path", "").strip()

        try:
            if game_path and os.path.exists(game_path):
                cmd = [game_path, "-skipStartVideos"]
                if mod_path:
                    cmd.append(f"-modsDirectory={mod_path}")
                subprocess.Popen(cmd)
                self.lbl_announcement.config(text="🚀 Spiel wird gestartet...", fg=self.ACCENT_GREEN)
            else:
                import webbrowser
                webbrowser.open("steam://run/2300320//-skipStartVideos/")
                self.lbl_announcement.config(text="🚀 Spiel über Steam gestartet...", fg=self.ACCENT_GREEN)
            
            self.after(1000, self.on_close)
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Spiel nicht starten:\n{e}")

    def on_close(self):
        self.is_closing: bool = True
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = LS25UserApp()
    app.mainloop()