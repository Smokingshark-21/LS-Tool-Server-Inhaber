# 🌾 LS25 Player & Admin Hub

Ein maßgeschneiderter Launcher und Administrator-Hub für *Landwirtschafts-Simulator 25* (LS25) Community-Server. Dieses Tool ermöglicht eine vollautomatische Mod-Synchronisation, Live-Server-Statistiken, direkte Spielstarts ohne Intro-Videos sowie eine zentrale Admin-Konsole zum Verwalten von Updates und Bannlisten.

---

## 🛠️ Systemvoraussetzungen (Admin-PC)

Um den Launcher für deine Community zu verwalten und zu kompilieren, benötigst du auf deinem Rechner:
* **Python** (ab Version 3.10+) mit installierten Bibliotheken (`Pillow`, etc.)[cite: 9, 10].
* **PyInstaller** (`pip install pyinstaller`) zum Kompilieren der App.
* **Inno Setup (Version 6)** zum Erstellen der `setup.exe` für die Spieler. Der Standardpfad (`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`) wird vom Admin-Panel automatisch erkannt.

---

## 📁 Server-Struktur (FTP)

Lege auf dem FTP-Server deines LS25-Servers folgende Ordnerstruktur an:
1. `/mods` – Hier liegen alle aktuellen `.zip`-Moddateien des Servers[cite: 9, 10].
2. `/Launcher` – Speicherort für die Konfiguration (`ls25_config.json`), die `user_app.exe` (für Auto-Updates) und die `setup.exe`[cite: 9, 10].
3. `/logs` – Der Standard-Log-Ordner deines LS25-Servers für die integrierte Mod-Fehleranalyse.

---

## ⚙️ Schritt-für-Schritt-Anleitung für Serverinhaber

### 1. Admin-Panel vorbereiten & starten
1. Lege `ls25_admin_app.py` und `user_app.py` in denselben lokalen Ordner.
2. Starte das Admin-Panel über die Konsole oder direkt per Python:
   ```bash
   python ls25_admin_app.py