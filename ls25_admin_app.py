import os
import sys
import json
import ftplib
import threading
import socket
import io
import re
import shutil
import subprocess
import urllib.request
import urllib.error
import mimetypes
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone
from PIL import Image, ImageTk

# --- Konstanten ---
REMOTE_LAUNCHER_DIR = "Launcher"
BUILD_FOLDER_PATH = "dist/user_app"
USER_APP_SCRIPT = "user_app.py"

class LS25AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Landwirtschafts-Simulator | Admin Hub")
        self.geometry("1200x950")
        self.minsize(1000, 750)

        self.config_filename = "ls25_config.json"
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
        self.config_data = self.load_config()
        self.setup_styles()
        self.create_widgets()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_window_icon(self):
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            for filename in ["logo.ico", "logo.png", "logo.jpg"]:
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

    def load_config(self):
        default_config = {
            "announcement": "Willkommen auf unserem Community Server!",
            "announcement_history": [
                "Willkommen auf unserem Community Server!",
                "Server wurde aktualisiert - Viel Spaß beim Spielen!"
            ],
            "webstats_url": "",
            "ftp_host": "",
            "ftp_port": 21,
            "ftp_user": "",
            "ftp_pass": "",
            "ftp_mods_path": "/mods",
            "ftp_config_remote_path": "/Launcher/ls25_config.json",
            "discord_bot_token": "",
            "discord_channel_id": "",
            "discord_ad_channel_id": "",
            "discord_update_channel_id": "",
            "discord_announcement_channel_id": "",
            "discord_status_channel_id": "",
            "discord_landwirt_role_id": "",
            "panel_users_history": [],
            "banned_panel_usernames": [],
            "banned_panel_ips": [],
            "banned_names": [],
            "banned_ips": []
        }
        if os.path.exists(self.config_filename):
            try:
                with open(self.config_filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_config.update(data)
                    return default_config
            except Exception:
                return default_config
        return default_config

    def save_config(self):
        try:
            for key, ent in self.config_entries.items():
                val = ent.get().strip()
                self.config_data[key] = val
                
                if key == "announcement" and val:
                    history = self.config_data.setdefault("announcement_history", [])
                    if val not in history:
                        history.insert(0, val)

            with open(self.config_filename, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)

            if "announcement" in self.config_entries:
                combobox = self.config_entries["announcement"]
                combobox['values'] = self.config_data.get("announcement_history", [])

            def upload_config_worker():
                try:
                    host = self.config_entries["ftp_host"].get()
                    port = int(self.config_entries["ftp_port"].get())
                    user = self.config_entries["ftp_user"].get()
                    password = self.config_entries["ftp_pass"].get()

                    if not host:
                        return

                    ftp = ftplib.FTP()
                    ftp.connect(host, port, timeout=5)
                    ftp.login(user, password)
                    ftp.set_pasv(True)

                    try:
                        ftp.cwd(REMOTE_LAUNCHER_DIR)
                    except Exception:
                        try:
                            ftp.cwd("/" + REMOTE_LAUNCHER_DIR)
                        except Exception:
                            pass

                    with open(self.config_filename, "rb") as f_in:
                        ftp.storbinary("STOR ls25_config.json", f_in)
                    ftp.quit()
                    self.log_message("✅ Config (ls25_config.json) erfolgreich auf FTP-Server hochgeladen.")
                except Exception as e:
                    self.log_message(f"⚠️ Konnte Config nicht per FTP hochladen: {e}")

            threading.Thread(target=upload_config_worker, daemon=True).start()

            messagebox.showinfo("Erfolg", "Konfiguration gespeichert und auf den Server geladen!")
            self.log_message("Konfiguration erfolgreich gespeichert und hochgeladen.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern der Konfiguration: {e}")
            self.log_message(f"Fehler beim Speichern der Config: {e}")

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
        style.configure("Danger.TButton", background=self.ACCENT_RED, foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#0d1117", foreground=self.TEXT_MAIN, insertcolor="#ffffff", borderwidth=1, relief="solid")
        style.configure("TCombobox", fieldbackground="#0d1117", foreground=self.TEXT_MAIN, borderwidth=1)
        style.configure("TLabel", background=self.BG_CARD, foreground=self.TEXT_MAIN, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=self.BG_DARK, foreground=self.ACCENT_AMBER, font=("Segoe UI", 16, "bold"))
        style.configure("Treeview", background=self.BG_CARD, foreground=self.TEXT_MAIN, fieldbackground=self.BG_CARD, rowheight=28, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=self.BG_CARD_ALT, foreground=self.ACCENT_AMBER, font=("Segoe UI", 10, "bold"))
        style.configure("Horizontal.TProgressbar", troughcolor=self.BG_DARK, background=self.ACCENT_GREEN, borderwidth=0)

    def create_widgets(self):
        header_frame = ttk.Frame(self, style="TFrame", padding=(20, 15))
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="🛠️ LS25 | Admin & Uploader Konsole", bg=self.BG_DARK, fg=self.ACCENT_AMBER, font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(header_frame, text="💾 Einstellungen Speichern", style="Accent.TButton", command=self.save_config).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        tab_dashboard = ttk.Frame(notebook, padding=15)
        tab_config = ttk.Frame(notebook, padding=15)
        tab_diagnose = ttk.Frame(notebook, padding=15)
        tab_ftp = ttk.Frame(notebook, padding=15)

        notebook.add(tab_dashboard, text="  📊 Live Dashboard  ")
        notebook.add(tab_config, text="  ⚙️ Steuerung & Sperren  ")
        notebook.add(tab_diagnose, text="  🩺 Live Diagnose & Logs  ")
        notebook.add(tab_ftp, text="  🚀 Installer & Uploader  ")

        # --- Tab 1: Live Dashboard ---
        dash_box = ttk.LabelFrame(tab_dashboard, text=" Live Server Übersicht ", padding=20)
        dash_box.pack(fill="both", expand=True)

        dash_top_frame = ttk.Frame(dash_box, style="Card.TFrame")
        dash_top_frame.pack(fill="x", pady=(0, 15))
        
        self.lbl_dash_status = tk.Label(dash_top_frame, text="Status: Bereit", bg=self.BG_CARD, fg=self.ACCENT_GREEN, font=("Segoe UI", 11, "bold"))
        self.lbl_dash_status.pack(side="left", padx=10, pady=10)
        
        ttk.Button(dash_top_frame, text="🔄 Status aktualisieren", command=self.refresh_dashboard_status).pack(side="right", padx=10, pady=10)

        cards_frame = ttk.Frame(dash_box, style="Card.TFrame")
        cards_frame.pack(fill="x", pady=(0, 15))

        self.card_name = self.create_metric_card(cards_frame, "SERVER NAME", "---", self.ACCENT_BLUE)
        self.card_name.pack(side="left", fill="x", expand=True, padx=5)

        self.card_map = self.create_metric_card(cards_frame, "KARTE", "---", self.ACCENT_AMBER)
        self.card_map.pack(side="left", fill="x", expand=True, padx=5)

        self.card_slots = self.create_metric_card(cards_frame, "SPIELER / SLOTS", "- / -", self.ACCENT_GREEN)
        self.card_slots.pack(side="left", fill="x", expand=True, padx=5)

        players_box = ttk.LabelFrame(dash_box, text=" Online Spieler ", padding=15)
        players_box.pack(fill="both", expand=True)

        self.dash_text_info = tk.Text(players_box, bg=self.BG_DARK, fg=self.TEXT_MAIN, height=10, bd=0, font=("Consolas", 10), padx=10, pady=10)
        self.dash_text_info.pack(fill="both", expand=True)
        self.refresh_dashboard_status()

        # --- Tab 2: Admin Steuerung & Sperren ---
        config_scroll = ttk.Scrollbar(tab_config)
        config_scroll.pack(side="right", fill="y")
        
        self.config_canvas = tk.Canvas(tab_config, bg=self.BG_CARD, yscrollcommand=config_scroll.set, bd=0, highlightthickness=0)
        self.config_canvas.pack(side="left", fill="both", expand=True)
        config_scroll.config(command=self.config_canvas.yview)
        
        config_frame = ttk.Frame(self.config_canvas, style="Card.TFrame", padding=20)
        self.config_window = self.config_canvas.create_window((0, 0), window=config_frame, anchor="nw")
        
        def on_canvas_configure(event):
            self.config_canvas.itemconfig(self.config_window, width=event.width)
            self.config_canvas.config(scrollregion=self.config_canvas.bbox("all"))
        self.config_canvas.bind("<Configure>", on_canvas_configure)

        self.config_entries = {}
        row = 0
        
        fields = [
            ("Ankündigung (User Panel):", "announcement", False),
            ("Webstats XML URL:", "webstats_url", False),
            ("FTP Host:", "ftp_host", False),
            ("FTP Port:", "ftp_port", False),
            ("FTP User:", "ftp_user", False),
            ("FTP Passwort:", "ftp_pass", True),
            ("FTP Mods Pfad:", "ftp_mods_path", False),
            ("Discord Bot Token:", "discord_bot_token", False),
            ("Discord Foto-Channel ID (Slideshow):", "discord_channel_id", False),
            ("Discord Werbe-Channel ID (Ad-Slideshow):", "discord_ad_channel_id", False),
            ("Discord Update-Channel ID (Setup.exe):", "discord_update_channel_id", False),
            ("Discord Ankündigungs-Channel ID:", "discord_announcement_channel_id", False),
            ("Discord Status-Channel ID (Live-Anzeige):", "discord_status_channel_id", False),
            ("Discord Landwirt Rollen-ID (@Landwirt):", "discord_landwirt_role_id", False)
        ]

        for label_text, key, is_password in fields:
            tk.Label(config_frame, text=label_text, bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=8)
            
            if key == "announcement":
                ent = ttk.Combobox(config_frame, width=58, state="normal")
                ent['values'] = self.config_data.get("announcement_history", [])
                current_val = str(self.config_data.get(key, ""))
                ent.set(current_val if current_val else (ent['values'][0] if ent['values'] else ""))
            elif "Channel ID" in label_text or "Rollen-ID" in label_text:
                ent = ttk.Combobox(config_frame, width=58, state="normal")
                current_val = str(self.config_data.get(key, ""))
                ent['values'] = [current_val] if current_val else []
                ent.set(current_val)
            else:
                ent = ttk.Entry(config_frame, width=60, show="*" if is_password else "")
                ent.insert(0, str(self.config_data.get(key, "")))
                
            ent.grid(row=row, column=1, sticky="ew", padx=15, pady=8)
            self.config_entries[key] = ent
            row += 1

        announcement_action_frame = ttk.Frame(config_frame, style="Card.TFrame")
        announcement_action_frame.grid(row=row, column=1, sticky="w", padx=15, pady=(0, 10))
        ttk.Button(announcement_action_frame, text="📢 Ankündigung sofort auf Discord posten", style="Accent.TButton", command=self.send_announcement_to_discord).pack(side="left")
        row += 1

        config_frame.columnconfigure(1, weight=1)

        history_frame = ttk.LabelFrame(config_frame, text=" 👥 Verbundene Spieler-Historie (Hub-Nutzer) ", padding=15)
        history_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=15)
        row += 1

        history_toolbar = ttk.Frame(history_frame, style="Card.TFrame")
        history_toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(history_toolbar, text="🔄 Liste vom Server laden", command=self.populate_user_history_from_ftp).pack(side="left")
        ttk.Button(history_toolbar, text="🚫 Ausgewählten User sperren", style="Danger.TButton", command=self.ban_user_from_history).pack(side="left", padx=10)

        self.tree_history = ttk.Treeview(history_frame, columns=("username", "ip"), show="headings", selectmode="browse", height=5)
        self.tree_history.heading("username", text="Spielername")
        self.tree_history.heading("ip", text="IP-Adresse")
        self.tree_history.column("username", width=250, anchor="w")
        self.tree_history.column("ip", width=250, anchor="center")
        self.tree_history.pack(fill="both", expand=True, pady=(0, 10))
        self.populate_user_history_local()

        banned_frame = ttk.LabelFrame(config_frame, text=" 🚫 Bannlisten Verwaltung ", padding=15)
        banned_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=15)
        
        ban_notebook = ttk.Notebook(banned_frame)
        ban_notebook.pack(fill="both", expand=True)

        tab_banned_users = ttk.Frame(ban_notebook, padding=10)
        tab_banned_ips = ttk.Frame(ban_notebook, padding=10)
        ban_notebook.add(tab_banned_users, text="  User Bannliste (Panel)  ")
        ban_notebook.add(tab_banned_ips, text="  IP Bannliste (Panel)  ")

        self.tree_banned_users = self.create_banned_tree(tab_banned_users, "banned_panel_usernames")
        self.tree_banned_ips = self.create_banned_tree(tab_banned_ips, "banned_panel_ips")

        # --- Tab 3: Live Diagnose & Logs & Mod-Analyse ---
        diag_box = ttk.LabelFrame(tab_diagnose, text=" 🩺 Systemprotokoll & Mod-Fehleranalyse ", padding=20)
        diag_box.pack(fill="both", expand=True)

        diag_btn_frame = ttk.Frame(diag_box, style="Card.TFrame")
        diag_btn_frame.pack(fill="x", pady=(0, 15))

        ttk.Button(diag_btn_frame, text="🔗 FTP Verbindung testen", command=self.test_ftp_connection).pack(side="left", padx=(0, 10))
        ttk.Button(diag_btn_frame, text="🔍 Mods & Ruckler analysieren (Detail-Check)", style="Accent.TButton", command=self.analyze_server_lag).pack(side="left")

        log_frame_inner = ttk.Frame(diag_box, style="Card.TFrame")
        log_frame_inner.pack(fill="both", expand=True)

        self.log_text_widget = tk.Text(log_frame_inner, bg=self.BG_DARK, fg=self.TEXT_MAIN, bd=0, font=("Consolas", 10), padx=10, pady=10)
        self.log_text_widget.pack(side="left", fill="both", expand=True)
        
        diag_scroll = ttk.Scrollbar(log_frame_inner, command=self.log_text_widget.yview)
        diag_scroll.pack(side="right", fill="y")
        self.log_text_widget.config(yscrollcommand=diag_scroll.set)
        
        self.log_message("Admin-Konsole erfolgreich gestartet.")

        # --- Tab 4: Installer & Uploader ---
        upload_box = ttk.LabelFrame(tab_ftp, text=" 🚀 Setup.exe & Auto-Update aktualisieren ", padding=20)
        upload_box.pack(fill="both", expand=True)

        tk.Label(upload_box, text=f"💡 Erstellt die neue 'setup.exe' und lädt sie optional per FTP hoch / postet sie auf Discord.", bg=self.BG_CARD, fg=self.TEXT_MAIN, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 10))
        
        options_frame = ttk.Frame(upload_box, style="Card.TFrame")
        options_frame.pack(anchor="w", pady=(0, 15))

        self.var_upload_ftp = tk.BooleanVar(value=True)
        self.var_upload_discord = tk.BooleanVar(value=True)

        chk_ftp = ttk.Checkbutton(options_frame, text="📥 Per FTP hochladen", variable=self.var_upload_ftp)
        chk_ftp.pack(side="left", padx=(0, 20))

        chk_disc = ttk.Checkbutton(options_frame, text="🤖 Auf Discord posten", variable=self.var_upload_discord)
        chk_disc.pack(side="left")

        btn_build_upload = ttk.Button(upload_box, text="🔨 Update bauen & ausführen", style="Accent.TButton", command=self.start_build_and_upload)
        btn_build_upload.pack(anchor="w", ipady=6, ipadx=10, pady=(0, 20))

        self.btn_upload_app = btn_build_upload

        self.lbl_upload_status = tk.Label(upload_box, text="Bereit.", bg=self.BG_CARD, fg=self.TEXT_MAIN, font=("Segoe UI", 10, "bold"))
        self.lbl_upload_status.pack(anchor="w", pady=(5, 5))
        
        self.progress_upload = ttk.Progressbar(upload_box, orient="horizontal", mode="determinate", style="Horizontal.TProgressbar")
        self.progress_upload.pack(fill="x", ipady=4)

    def fetch_server_status(self):
        try:
            url = self.config_entries["webstats_url"].get() if hasattr(self, 'config_entries') else self.config_data.get("webstats_url", "")
            if not url:
                return {"online": False, "name": "Nicht konfiguriert", "map": "---", "slots": "- / -", "players": []}

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()
                if not xml_data:
                    return {"online": False, "name": "Offline", "map": "---", "slots": "- / -", "players": []}

                root = ET.fromstring(xml_data)
                s_name = root.attrib.get('name', '').strip()
                map_name = root.attrib.get('mapName', '').strip()
                slots = root.attrib.get('slots', '0').strip()

                if not map_name or map_name.lower() in ["none", "unbekannt", ""]:
                    return {"online": False, "name": s_name or "Community Server", "map": "---", "slots": f"0 / {slots}", "players": []}

                players = []
                for s in root.findall('Slots'):
                    for p in s.findall('Player'):
                        if p.attrib.get('isUsed') == 'true':
                            players.append(p.text or "Unbekannt")

                num_players = len(players)
                return {
                    "online": True,
                    "name": s_name if s_name else "Community Server",
                    "map": map_name,
                    "slots": f"{num_players} / {slots}",
                    "players": players
                }
        except Exception:
            return {"online": False, "name": "Offline", "map": "---", "slots": "- / -", "players": []}

    def send_announcement_to_discord(self):
        token = self.config_entries["discord_bot_token"].get().strip()
        channel_id = self.config_entries["discord_announcement_channel_id"].get().strip()
        announcement_text = self.config_entries["announcement"].get().strip()
        role_id = self.config_entries["discord_landwirt_role_id"].get().strip()

        if not token or not channel_id:
            messagebox.showwarning("Fehler", "Bitte hinterlege zuerst den Discord Bot Token und die Discord Ankündigungs-Channel ID in den Konfigurationen.")
            return

        if not announcement_text:
            messagebox.showwarning("Hinweis", "Bitte gib eine Ankündigung ein oder wähle eine Vorlage aus.")
            return

        if announcement_text not in self.config_data.get("announcement_history", []):
            self.config_data.setdefault("announcement_history", []).insert(0, announcement_text)
            self.save_config()

        def worker():
            self.log_message("📢 Sende Ankündigung an Discord...")
            try:
                headers = {
                    "Authorization": f"Bot {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "DiscordBot (AdminHub, 1.0)"
                }
                
                get_url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=20"
                req_get = urllib.request.Request(get_url, headers=headers)
                try:
                    with urllib.request.urlopen(req_get, timeout=5) as resp:
                        messages = json.loads(resp.read().decode("utf-8"))
                        for msg in messages:
                            content = msg.get("content", "")
                            if "Server-Ankündigung" in content:
                                old_msg_id = msg.get("id")
                                del_url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{old_msg_id}"
                                req_del = urllib.request.Request(del_url, headers=headers, method="DELETE")
                                try:
                                    urllib.request.urlopen(req_del, timeout=5)
                                    self.log_message(f"🗑️ Alte Ankündigung ({old_msg_id}) gelöscht.")
                                except Exception:
                                    pass
                except Exception as e:
                    self.log_message(f"⚠️ Konnte alte Ankündigungen nicht löschen: {e}")

                post_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                role_mention = f"<@&{role_id}>" if role_id else "@Landwirt"
                payload = json.dumps({"content": f"📢 **Server-Ankündigung:**\n{announcement_text}\n\n{role_mention}"})
                
                req = urllib.request.Request(post_url, data=payload.encode("utf-8"), headers=headers, method="POST")
                
                with urllib.request.urlopen(req, timeout=10) as resp:
                    self.log_message("✅ Neue Ankündigung erfolgreich im Ankündigungs-Channel gepostet!")
                    self.after(0, lambda: messagebox.showinfo("Erfolg", "Ankündigung wurde erfolgreich im Discord-Kanal veröffentlicht!"))
            except Exception as e:
                self.log_message(f"❌ Fehler beim Senden der Ankündigung: {e}")
                self.after(0, lambda: messagebox.showerror("Fehler", f"Konnte Ankündigung nicht senden:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    def create_metric_card(self, parent, title, initial_val, border_color):
        card_outer = tk.Frame(parent, bg=border_color, bd=1)
        card_inner = tk.Frame(card_outer, bg=self.BG_CARD_ALT)
        card_inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(card_inner, text=title, bg=self.BG_CARD_ALT, fg=self.TEXT_MUTED, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        lbl_val = tk.Label(card_inner, text=initial_val, bg=self.BG_CARD_ALT, fg=self.TEXT_MAIN, font=("Segoe UI", 13, "bold"), anchor="w")
        lbl_val.pack(fill="x", padx=12, pady=(4, 12))
        card_outer.lbl_val = lbl_val
        return card_outer

    def populate_user_history_local(self):
        for item in self.tree_history.get_children():
            self.tree_history.delete(item)
        
        self.config_data = self.load_config()
        history = self.config_data.get("panel_users_history", [])
        for entry in history:
            if isinstance(entry, dict):
                u = entry.get("username", "Unbekannt")
                ip = entry.get("ip", "Unbekannt")
                self.tree_history.insert("", "end", values=(u, ip))

    def populate_user_history_from_ftp(self):
        def worker():
            self.log_message("Lade Spieler-Historie vom FTP-Server...")
            try:
                host = self.config_entries["ftp_host"].get()
                port = int(self.config_entries["ftp_port"].get())
                user = self.config_entries["ftp_user"].get()
                password = self.config_entries["ftp_pass"].get()

                if not host:
                    return

                ftp = ftplib.FTP()
                ftp.connect(host, port, timeout=5)
                ftp.login(user, password)
                ftp.set_pasv(True)

                try:
                    ftp.cwd(REMOTE_LAUNCHER_DIR)
                except Exception:
                    try:
                        ftp.cwd("/" + REMOTE_LAUNCHER_DIR)
                    except Exception:
                        pass

                bio = io.BytesIO()
                try:
                    ftp.retrbinary("RETR ls25_config.json", bio.write)
                    remote_data = json.loads(bio.getvalue().decode("utf-8"))
                    if "panel_users_history" in remote_data:
                        self.config_data["panel_users_history"] = remote_data["panel_users_history"]
                        with open(self.config_filename, "w", encoding="utf-8") as f:
                            json.dump(self.config_data, f, indent=4, ensure_ascii=False)
                        self.log_message("✅ Spieler-Historie erfolgreich vom Server geladen.")
                except Exception as e:
                    self.log_message(f"⚠️ Konnte ls25_config.json nicht laden: {e}")

                ftp.quit()
                self.after(0, self.populate_user_history_local)
            except Exception as e:
                self.log_message(f"❌ Fehler beim Laden der Spieler-Historie: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def ban_user_from_history(self):
        selected = self.tree_history.selection()
        if not selected:
            messagebox.showwarning("Hinweis", "Bitte wähle einen Spieler aus der Liste aus.")
            return
        
        item = self.tree_history.item(selected[0])
        username, ip = item["values"]

        if messagebox.askyesno("Bestätigung", f"Möchtest du den Spieler '{username}' (IP: {ip}) wirklich sperren?"):
            if username not in self.config_data.get("banned_panel_usernames", []):
                self.config_data.setdefault("banned_panel_usernames", []).append(username)
            if ip not in self.config_data.get("banned_panel_ips", []):
                self.config_data.setdefault("banned_panel_ips", []).append(ip)
            
            self.save_config()
            self.populate_banned_tree(self.tree_banned_users, "banned_panel_usernames")
            self.populate_banned_tree(self.tree_banned_ips, "banned_panel_ips")
            messagebox.showinfo("Erfolg", f"Spieler {username} wurde gesperrt.")
            self.log_message(f"Spieler {username} (IP: {ip}) wurde über die Historie gesperrt.")

    def log_message(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}\n"
        try:
            if hasattr(self, 'log_text_widget') and self.log_text_widget.winfo_exists():
                self.log_text_widget.insert(tk.END, full_msg)
                self.log_text_widget.see(tk.END)
        except Exception:
            pass
        print(f"LOG: {message}")

    def refresh_dashboard_status(self):
        try:
            self.dash_text_info.delete("1.0", tk.END)
            self.dash_text_info.insert(tk.END, "Lade Live-Server Status...\n")
            
            status_info = self.fetch_server_status()
            
            self.card_name.lbl_val.config(text=status_info["name"])
            self.card_map.lbl_val.config(text=status_info["map"])
            self.card_slots.lbl_val.config(text=status_info["slots"])

            self.dash_text_info.delete("1.0", tk.END)
            if status_info["online"]:
                players = status_info["players"]
                if players:
                    self.dash_text_info.insert(tk.END, f"Aktuell online ({len(players)} Spieler):\n" + "\n".join([f" • {p}" for p in players]))
                else:
                    self.dash_text_info.insert(tk.END, "Derzeit sind keine Spieler online.")
            else:
                self.dash_text_info.insert(tk.END, "⚠️ Der Server ist derzeit OFFLINE oder nicht erreichbar.")
        except Exception as e:
            self.dash_text_info.delete("1.0", tk.END)
            self.dash_text_info.insert(tk.END, f"❌ Fehler beim Abrufen der Webstats: {e}\n")
            self.card_name.lbl_val.config(text="Fehler")

    def test_ftp_connection(self):
        def worker():
            self.log_message("Teste FTP-Verbindung...")
            try:
                host = self.config_entries["ftp_host"].get()
                port = int(self.config_entries["ftp_port"].get())
                user = self.config_entries["ftp_user"].get()
                password = self.config_entries["ftp_pass"].get()

                if not host:
                    messagebox.showwarning("Hinweis", "Bitte FTP-Host eingeben.")
                    return

                ftp = ftplib.FTP()
                ftp.connect(host, port, timeout=5)
                ftp.login(user, password)
                ftp.quit()
                self.log_message("✅ FTP-Verbindung erfolgreich hergestellt!")
                messagebox.showinfo("Erfolg", "FTP-Verbindung erfolgreich!")
            except Exception as e:
                self.log_message(f"❌ FTP-Verbindung fehlgeschlagen: {e}")
                messagebox.showerror("Fehler", f"FTP-Verbindung fehlgeschlagen:\n{e}")
        threading.Thread(target=worker, daemon=True).start()

    def analyze_server_lag(self):
        def worker():
            self.log_message("🔍 Starte detaillierte Mod- und Fehler-Analyse im Ordner '/logs'...")
            ftp = None
            try:
                host = self.config_entries["ftp_host"].get()
                port = int(self.config_entries["ftp_port"].get())
                user = self.config_entries["ftp_user"].get()
                password = self.config_entries["ftp_pass"].get()

                if not host:
                    return

                ftp = ftplib.FTP()
                ftp.connect(host, port, timeout=8)
                ftp.login(user, password)
                ftp.set_pasv(True)

                log_content = None
                latest_log_name = ""

                try:
                    ftp.cwd("/logs")
                    files = ftp.nlst()
                    log_files = [f for f in files if f.startswith("log_") and f.endswith(".txt")]
                    if log_files:
                        log_files.sort()
                        latest_log_name = log_files[-1]
                        
                        bio = io.BytesIO()
                        ftp.retrbinary(f"RETR {latest_log_name}", bio.write)
                        log_content = bio.getvalue().decode("utf-8", errors="ignore")
                        self.log_message(f"📄 Neueste Log-Datei geladen: /logs/{latest_log_name}")
                except Exception as e:
                    self.log_message(f"⚠️ Konnte /logs Ordner nicht lesen: {e}")

                ftp.quit()

                if not log_content:
                    self.log_message("⚠️ Konnte keine Log-Datei im Ordner '/logs' finden.")
                    messagebox.showwarning("Diagnose", "Konnte keine Log-Datei im '/logs' Ordner finden.")
                    return

                lines = log_content.splitlines()
                mod_errors = {}

                mod_path_pattern = re.compile(r"mods[/\\]([^/\\]+)", re.IGNORECASE)
                mod_zip_pattern = re.compile(r"([a-zA-Z0-9_-]+\.zip)", re.IGNORECASE)

                for i, line in enumerate(lines):
                    lower_line = line.lower()
                    if "error" in lower_line or "exception" in lower_line or "stack traceback" in lower_line or " lua error" in lower_line:
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)
                        context_snippet = "\n".join(lines[context_start:context_end])

                        found_mod = "Unbekannter Mod / Basisspiel"
                        match_path = mod_path_pattern.search(context_snippet)
                        if match_path:
                            found_mod = match_path.group(1)
                        else:
                            match_zip = mod_zip_pattern.search(context_snippet)
                            if match_zip:
                                found_mod = match_zip.group(1)

                        if found_mod not in mod_errors:
                            mod_errors[found_mod] = []
                        
                        clean_line = re.sub(r"^\[\d{2}:\d{2}:\d{2}\]\s+→\s+[\d:\.\-\s]+\s*", "", line.strip())
                        if clean_line not in mod_errors[found_mod]:
                            mod_errors[found_mod].append(clean_line)

                self.log_message("\n" + "="*50)
                self.log_message(" 🛠️  ÜBERSICHTLICHE MOD-FEHLERANALYSE")
                self.log_message("="*50)
                self.log_message(f"📁 Analysierte Log-Datei: {latest_log_name}")

                if not mod_errors:
                    self.log_message("✅ Keine Fehler in den Mods gefunden! Alles läuft sauber.")
                else:
                    for mod_name, errs in sorted(mod_errors.items(), key=lambda x: len(x[1]), reverse=True):
                        self.log_message(f"\n📦 MOD: {mod_name}")
                        self.log_message(f"   ⚠️ Gefundene Fehler: {len(errs)}")
                        for err in errs[:5]:
                            self.log_message(f"      ➔ {err}")
                        if len(errs) > 5:
                            self.log_message(f"      ... und {len(errs) - 5} weitere ähnliche Fehler.")

                self.log_message("="*50 + "\n")

            except Exception as e:
                self.log_message(f"❌ Fehler bei der Mod-Analyse: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def create_banned_tree(self, parent, config_key):
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(fill="both", expand=True)
        
        toolbar = ttk.Frame(frame, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        ent_val = ttk.Entry(toolbar)
        ent_val.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        tree = ttk.Treeview(frame, columns=("value",), show="headings", selectmode="browse")
        tree.heading("value", text="Eintrag")
        tree.column("value", anchor="center")
        tree.pack(fill="both", expand=True, pady=(0, 10))
        
        btn_add = ttk.Button(toolbar, text="➕ Hinzufügen", command=lambda k=config_key, e=ent_val, t=tree: self.add_ban(k, e, t))
        btn_add.pack(side="left")
        btn_rem = ttk.Button(toolbar, text="➖ Entfernen", style="Danger.TButton", command=lambda k=config_key, t=tree: self.remove_ban(k, t))
        btn_rem.pack(side="left", padx=10)

        self.populate_banned_tree(tree, config_key)
        return tree

    def populate_banned_tree(self, tree, config_key):
        for item in tree.get_children():
            tree.delete(item)
        for val in self.config_data.get(config_key, []):
            tree.insert("", "end", values=(val,))

    def add_ban(self, config_key, entry_widget, tree_widget):
        val = entry_widget.get().strip()
        if not val: return
        if val not in self.config_data.get(config_key, []):
            if config_key not in self.config_data: self.config_data[config_key] = []
            self.config_data[config_key].append(val)
            self.populate_banned_tree(tree_widget, config_key)
            entry_widget.delete(0, tk.END)
            self.save_config()
            self.log_message(f"Eintrag zu {config_key} hinzugefügt: {val}")

    def remove_ban(self, config_key, tree_widget):
        selected = tree_widget.selection()
        if not selected: return
        item = tree_widget.item(selected[0])
        val = item["values"][0]
        if val in self.config_data.get(config_key, []):
            self.config_data[config_key].remove(val)
            self.populate_banned_tree(tree_widget, config_key)
            self.save_config()
            self.log_message(f"Eintrag aus {config_key} entfernt: {val}")

    def upload_setup_to_discord(self, token, channel_id, file_path):
        if not token or not channel_id:
            self.log_message("ℹ️ Kein Discord Token oder Update-Channel ID hinterlegt – Überspringe Discord-Upload.")
            return

        self.log_message("🤖 Verbinde mit Discord API für den Update-Channel...")
        headers = {
            "Authorization": f"Bot {token}",
            "User-Agent": "DiscordBot (AdminHub, 1.0)"
        }

        try:
            get_url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=20"
            req_get = urllib.request.Request(get_url, headers=headers)
            try:
                with urllib.request.urlopen(req_get, timeout=5) as resp:
                    messages = json.loads(resp.read().decode("utf-8"))
                    for msg in messages:
                        author = msg.get("author", {})
                        if author.get("bot", False):
                            msg_id = msg.get("id")
                            del_url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}"
                            req_del = urllib.request.Request(del_url, headers=headers, method="DELETE")
                            try:
                                urllib.request.urlopen(req_del, timeout=5)
                                self.log_message(f"🗑️ Alte Update-Bot-Nachricht ({msg_id}) im Update-Channel gelöscht.")
                            except Exception:
                                pass
            except urllib.error.HTTPError as he:
                if he.code == 401:
                    self.log_message("❌ Discord Fehler: Ungültiger Bot-Token (HTTP 401 Unauthorized).")
                    return
                else:
                    raise he

            self.log_message("🚀 Lade neue 'setup.exe' im Update-Channel hoch...")
            post_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            filename = os.path.basename(file_path)

            announcement_text = self.config_entries["announcement"].get().strip()
            role_id = self.config_entries["discord_landwirt_role_id"].get().strip()
            role_mention = f"<@&{role_id}>" if role_id else "@Landwirt"
            
            content_msg = f"🚀 **Neues Player Hub Update verfügbar!**\n{announcement_text}\n\nLade dir hier die aktuelle `setup.exe` herunter und installiere sie mit einem Doppelklick:\n\n{role_mention}"

            body = bytearray()
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="content"\r\n\r\n{content_msg}\r\n'.encode("utf-8"))

            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'.encode("utf-8"))
            body.extend(f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8"))

            with open(file_path, "rb") as f_in:
                body.extend(f_in.read())

            body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

            req_post = urllib.request.Request(post_url, data=body, headers={
                "Authorization": f"Bot {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "DiscordBot (AdminHub, 1.0)"
            }, method="POST")

            with urllib.request.urlopen(req_post, timeout=30) as resp:
                self.log_message("✅ Neue 'setup.exe' mit Ankündigung erfolgreich im Update-Channel veröffentlicht!")

        except Exception as e:
            self.log_message(f"⚠️ Discord-Upload übersprungen / abgebrochen: {e}")

    def start_build_and_upload(self):
        if not os.path.exists(USER_APP_SCRIPT):
            messagebox.showwarning("Fehler", f"Die Skriptdatei '{USER_APP_SCRIPT}' wurde im aktuellen Ordner nicht gefunden.")
            return

        if not messagebox.askyesno("Bestätigung", f"Möchtest du den Build- und Upload-Vorgang für '{USER_APP_SCRIPT}' starten?"):
            return

        try:
            host = self.config_entries["ftp_host"].get()
            port = int(self.config_entries["ftp_port"].get())
            user = self.config_entries["ftp_user"].get()
            password = self.config_entries["ftp_pass"].get()
            bot_token = self.config_entries["discord_bot_token"].get().strip()
            update_channel_id = self.config_entries["discord_update_channel_id"].get().strip()
        except ValueError:
            messagebox.showwarning("Fehler", "Ungültige Verbindungsdaten in der Konfiguration.")
            return

        do_ftp = self.var_upload_ftp.get()
        do_discord = self.var_upload_discord.get()

        self.btn_upload_app.config(state="disabled")
        self.lbl_upload_status.config(text="Kompiliere App...", fg=self.ACCENT_BLUE)
        self.progress_upload["value"] = 0
        self.update()

        threading.Thread(target=self.build_uploader_thread, args=(host, port, user, password, bot_token, update_channel_id, do_ftp, do_discord), daemon=True).start()

    def build_uploader_thread(self, host, port, user, password, bot_token, update_channel_id, do_ftp, do_discord):
        try:
            self.log_message("🔨 Starte PyInstaller Kompilierung...")
            cmd_py = [sys.executable, "-m", "PyInstaller", "--onedir", "--noconsole", "--icon=logo.ico", USER_APP_SCRIPT]
            
            process = subprocess.Popen(cmd_py, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                line_str = line.strip()
                if line_str:
                    print(f"PyInstaller: {line_str}")
            process.wait()

            if process.returncode != 0:
                self.log_message("❌ PyInstaller Kompilierung fehlgeschlagen!")
                self.after(0, lambda: self.show_upload_result(False, "PyInstaller Build fehlgeschlagen."))
                return

            self.log_message("✅ PyInstaller Build erfolgreich! Erstelle Inno Setup Skript...")
            self.after(0, lambda: self.lbl_upload_status.config(text="Erstelle Installer..."))

            iss_content = f"""[Setup]
AppName=LS25 Player Hub
AppVersion=1.1.0
DefaultDirName={{autopf}}\\LS25 Player Hub
DefaultGroupName=LS25 Player Hub
OutputDir=dist
OutputBaseFilename=LS25_PlayerHub_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "{BUILD_FOLDER_PATH}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autodesktop}}\\LS25 Player Hub"; Filename: "{{app}}\\user_app.exe"; Tasks: desktopicon
Name: "{{autoprograms}}\\LS25 Player Hub\\Player Hub"; Filename: "{{app}}\\user_app.exe"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop erstellen"; GroupDescription: "Zusätzliche Aufgaben:"
"""
            iss_path = "build_setup.iss"
            with open(iss_path, "w", encoding="utf-8") as f_iss:
                f_iss.write(iss_content)

            iscc_exe = shutil.which("iscc")
            if not iscc_exe:
                possible_paths = [
                    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                    r"C:\Program Files\Inno Setup 6\ISCC.exe",
                    os.path.expandvars(r"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe")
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        iscc_exe = p
                        break

            if not iscc_exe:
                self.log_message("❌ Inno Setup Compiler (ISCC.exe) wurde im System nicht gefunden!")
                self.after(0, lambda: self.show_upload_result(False, "Inno Setup Compiler (ISCC.exe) wurde nicht gefunden."))
                return

            self.log_message(f"🔨 Verwende Inno Setup: {iscc_exe}")
            self.log_message("🔨 Erstelle 'LS25_PlayerHub_Setup.exe'...")
            
            process_iscc = subprocess.Popen([iscc_exe, iss_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process_iscc.stdout:
                line_str = line.strip()
                if line_str:
                    print(f"InnoSetup: {line_str}")
            process_iscc.wait()

            setup_exe_path = os.path.join("dist", "LS25_PlayerHub_Setup.exe")
            user_exe_path = os.path.join("dist", "user_app", "user_app.exe")

            if not os.path.exists(setup_exe_path) or not os.path.exists(user_exe_path):
                self.log_message("❌ Build-Dateien wurden nicht gefunden!")
                self.after(0, lambda: self.show_upload_result(False, "Fehler beim Erstellen der Dateien."))
                return

            success_actions = ["Lokaler Build (Setup.exe & EXE) erfolgreich"]

            if do_ftp and host:
                self.log_message("🚀 Lade Dateien per FTP hoch...")
                self.after(0, lambda: self.lbl_upload_status.config(text="Lade Dateien per FTP hoch..."))

                ftp = ftplib.FTP()
                ftp.connect(host, port, timeout=10)
                ftp.login(user, password)
                ftp.set_pasv(True)

                try:
                    ftp.cwd(REMOTE_LAUNCHER_DIR)
                except ftplib.error_perm:
                    try:
                        ftp.mkd(REMOTE_LAUNCHER_DIR)
                        ftp.cwd(REMOTE_LAUNCHER_DIR)
                    except Exception as ex:
                        self.log_message(f"⚠️ Konnte Verzeichnis '{REMOTE_LAUNCHER_DIR}' nicht betreten: {ex}")
                        ftp.cwd("/" + REMOTE_LAUNCHER_DIR)

                with open(setup_exe_path, "rb") as f_in:
                    ftp.storbinary("STOR setup.exe", f_in)
                with open(user_exe_path, "rb") as f_in:
                    ftp.storbinary("STOR user_app.exe", f_in)

                ftp.quit()
                self.log_message("✅ FTP-Upload erfolgreich abgeschlossen.")
                success_actions.append("FTP-Server aktualisiert")
            else:
                self.log_message("ℹ️ FTP-Upload übersprungen.")

            if do_discord:
                self.after(0, lambda: self.lbl_upload_status.config(text="Poste Update im Update-Channel..."))
                self.upload_setup_to_discord(bot_token, update_channel_id, setup_exe_path)
                success_actions.append("Im Discord Update-Channel veröffentlicht")
            else:
                self.log_message("ℹ️ Discord-Post übersprungen.")

            self.log_message("✅ Vorgang erfolgreich beendet!")
            result_message = "Vorgang erfolgreich abgeschlossen!\n- " + "\n- ".join(success_actions)
            self.after(0, lambda: self.show_upload_result(True, result_message))

        except Exception as e:
            err_msg = str(e)
            self.log_message(f"❌ Fehler beim Vorgang: {err_msg}")
            self.after(0, lambda msg=err_msg: self.show_upload_result(False, f"Fehler: {msg}"))

    def show_upload_result(self, success, message):
        if success:
            self.lbl_upload_status.config(text="✅ Fertiggestellt!", fg=self.ACCENT_GREEN)
            messagebox.showinfo("Erfolg", message)
        else:
            self.lbl_upload_status.config(text="❌ Vorgang fehlgeschlagen.", fg=self.ACCENT_RED)
            messagebox.showerror("Fehler", f"Vorgang fehlgeschlagen:\n{message}")
        self.progress_upload["value"] = 0
        self.btn_upload_app.config(state="normal")

    def on_close(self):
        if messagebox.askyesno("Beenden", "Admin Panel wirklich schließen?"):
            self.destroy()

if __name__ == "__main__":
    app = LS25AdminApp()
    app.mainloop()