import requests
import ctypes
import os
import json
import threading
import schedule
import time
import random
import re
import sys
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import messagebox
import pystray
from pystray import MenuItem
from PIL import Image, ImageDraw

# ========== Resource path for PyInstaller ==========
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ========== Config path in AppData (writable) ==========
def get_config_path():
    appdata = os.environ.get('APPDATA')
    if appdata:
        config_dir = os.path.join(appdata, 'NASA Wallpaper')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'nasa_config.json')
    else:
        # Fallback: use current directory (but might fail in Program Files)
        return os.path.join(os.path.expanduser('~'), 'Documents', 'nasa_config.json')

CONFIG_FILE = get_config_path()

# ========== Settings ==========
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME = "NASA Wallpaper"
VERSION = "7.4"
SAVE_DIR = os.path.join(os.environ['USERPROFILE'], "Pictures", "NASA_APOD")
MIN_FILE_SIZE_MB = 1.0
AUTO_START_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTO_START_NAME = "NASAWallpaper"

# ========== API Key ==========
API_KEY = "PDqruqTzZ28nDgZ71DrEBytGGuo1WpPEbgJbt8tE"

# ========== Color Palette ==========
COLORS = {
    "bg": "#0B0E17",
    "primary": "#0B3D91",
    "primary_hover": "#1A5BC4",
    "secondary": "#FF6B35",
    "secondary_hover": "#FF8A5C",
    "success": "#2E7D32",
    "danger": "#C62828",
    "folder": "#4A5568",
    "folder_hover": "#5A6B7C",
    "text": "#E8EDF5",
    "text_muted": "#8899AA",
    "card_bg": "#141A26",
    "border": "#1E2A3A"
}

# ========== Config ==========
class Config:
    def __init__(self):
        self.interval_hours = 4
        self.last_update = None

    def save(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.__dict__, f, indent=2)

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        setattr(self, k, v)
                return True
            except:
                return False
        return False

# ========== Helper Functions ==========
def sanitize_filename(title):
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'[^\w\s-]', '', safe).strip()
    safe = re.sub(r'[-\s]+', '_', safe)
    return safe[:200] if len(safe) > 200 else safe

def get_existing_titles():
    titles = set()
    if not os.path.exists(SAVE_DIR):
        return titles
    for f in os.listdir(SAVE_DIR):
        if f.startswith("apod_") and f.endswith(".jpg"):
            titles.add(f[5:-4])
    return titles

def get_apod_data(api_key, date):
    try:
        resp = requests.get(
            f"https://api.nasa.gov/planetary/apod?api_key={api_key}&date={date}",
            timeout=15
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get('media_type') == 'image' and data.get('hdurl'):
            return {
                'url': data['hdurl'],
                'title': data.get('title', 'No Title'),
                'explanation': data.get('explanation', '')
            }
        return None
    except:
        return None

def set_wallpaper(image_path):
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "10")
        winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
        winreg.CloseKey(key)
    except:
        pass
    ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)

def update_wallpaper():
    try:
        existing_titles = get_existing_titles()
        tried_dates = set()
        
        for _ in range(60):
            days_ago = random.randint(1, 30)
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            if date in tried_dates:
                continue
            tried_dates.add(date)
            
            apod = get_apod_data(API_KEY, date)
            if not apod:
                continue
            
            safe_title = sanitize_filename(apod['title'])
            if safe_title in existing_titles:
                continue
            
            os.makedirs(SAVE_DIR, exist_ok=True)
            temp_path = os.path.join(SAVE_DIR, f"temp_{date}.jpg")
            
            img_data = requests.get(apod['url'], timeout=30)
            if img_data.status_code != 200:
                continue
            
            with open(temp_path, 'wb') as f:
                f.write(img_data.content)
            
            if os.path.getsize(temp_path) / (1024 * 1024) < MIN_FILE_SIZE_MB:
                os.remove(temp_path)
                continue
            
            final_path = os.path.join(SAVE_DIR, f"apod_{safe_title}.jpg")
            os.rename(temp_path, final_path)
            set_wallpaper(final_path)
            
            config.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            config.save()
            return f"✅ Success: {apod['title']} ({os.path.getsize(final_path) / (1024*1024):.2f} MB)"
        
        return "⚠️ No new high-quality images. Try again later."
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ========== Startup ==========
def add_to_startup():
    try:
        import winreg
        exe_path = sys.executable
        if exe_path.endswith("python.exe"):
            cmd = f'"{exe_path}" "{os.path.abspath(sys.argv[0])}"'
        else:
            cmd = f'"{exe_path}"'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTO_START_REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, AUTO_START_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except:
        return False

# ========== Tray Icon ==========
def create_default_icon():
    img = Image.new('RGB', (64, 64), color=COLORS["primary"])
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=COLORS["secondary"], outline=COLORS["text"], width=2)
    return img

# ========== Main App ==========
class NASAApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.geometry("420x510")
        self.root.resizable(False, False)
        self.root.configure(fg_color=COLORS["bg"])
        
        icon_path = resource_path('icon.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except:
                pass

        global config
        config = Config()
        if not config.load():
            # Create default config if doesn't exist
            config.save()

        self.schedule_running = False
        self.schedule_thread = None
        self.tray_icon = None

        self.build_ui()

        if config.interval_hours > 0:
            self.start_schedule()

        self.root.bind('<F5>', lambda e: self.manual_update())
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTO_START_REG_KEY, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, AUTO_START_NAME)
            winreg.CloseKey(key)
        except:
            add_to_startup()

    def build_ui(self):
        card = ctk.CTkFrame(self.root, fg_color=COLORS["card_bg"], corner_radius=16, border_width=1, border_color=COLORS["border"])
        card.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(card, text="🌌 NASA Astronomy Picture", font=("Segoe UI", 20, "bold"), text_color=COLORS["text"]).pack(pady=(25, 2))
        ctk.CTkLabel(card, text="PC BAAZ · Premium Software", font=("Segoe UI", 12, "bold"), text_color=COLORS["secondary"]).pack()
        ctk.CTkLabel(card, text="Handpicked high-quality images from NASA's last 30 days", font=("Segoe UI", 10), text_color=COLORS["text_muted"]).pack(pady=(4, 0))

        self.status_label = ctk.CTkLabel(card, text="🟢 Ready", font=("Segoe UI", 15, "bold"), text_color=COLORS["text"])
        self.status_label.pack(pady=(18, 5))

        self.last_update_label = ctk.CTkLabel(
            card,
            text=f"Last update: {config.last_update if config.last_update else 'Never'}",
            font=("Segoe UI", 11),
            text_color=COLORS["text_muted"]
        )
        self.last_update_label.pack(pady=5)

        ctk.CTkFrame(card, height=1, fg_color=COLORS["border"]).pack(pady=15, padx=30, fill="x")

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=10, padx=20)

        ctk.CTkButton(btn_frame, text="🔄 Update Now", command=self.manual_update,
                      width=240, height=45, font=("Segoe UI", 14, "bold"),
                      fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                      corner_radius=10).pack(pady=6)

        ctk.CTkButton(btn_frame, text="📂 Open Images Folder",
                      command=lambda: os.startfile(SAVE_DIR) if os.path.exists(SAVE_DIR) else messagebox.showerror("Error", "Folder not found"),
                      width=240, height=40, font=("Segoe UI", 13, "bold"),
                      fg_color=COLORS["folder"], hover_color=COLORS["folder_hover"],
                      corner_radius=10).pack(pady=6)

        ctk.CTkButton(btn_frame, text="🗑 Clear Cache (Keep Last 5)",
                      command=self.clear_cache,
                      width=240, height=40, font=("Segoe UI", 13, "bold"),
                      fg_color=COLORS["danger"], hover_color="#B71C1C",
                      corner_radius=10).pack(pady=6)

        self.auto_btn = ctk.CTkButton(btn_frame, text="⏰ Auto Update (4h)",
                                      command=self.toggle_auto_update,
                                      width=240, height=40, font=("Segoe UI", 13, "bold"),
                                      fg_color=COLORS["success"], hover_color="#1B5E20",
                                      corner_radius=10)
        self.auto_btn.pack(pady=6)

    # ---------- System Tray ----------
    def hide_to_tray(self):
        self.root.withdraw()
        if self.tray_icon is None:
            self.setup_tray_icon()
        self.tray_icon.visible = True

    def show_window(self):
        if self.tray_icon:
            self.tray_icon.visible = False
        self.root.deiconify()
        self.root.focus_force()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

    def quit_app(self):
        self.schedule_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()

    def setup_tray_icon(self):
        icon_path = resource_path('icon.ico')
        if os.path.exists(icon_path):
            try:
                image = Image.open(icon_path)
            except:
                image = create_default_icon()
        else:
            image = create_default_icon()

        menu = (
            MenuItem('Show Panel', self.show_window),
            MenuItem('Update Now', self.manual_update_tray),
            MenuItem('Exit', self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("nasa_wallpaper", image, APP_NAME, menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def manual_update_tray(self, icon=None, item=None):
        self.manual_update()

    # ---------- Core Functions ----------
    def manual_update(self):
        self.status_label.configure(text="⏳ Searching...", text_color="#FFB74D")
        self.root.update()

        def do():
            result = update_wallpaper()
            self.root.after(0, lambda: self.after_update(result))

        threading.Thread(target=do, daemon=True).start()

    def after_update(self, result):
        color = COLORS["text"] if "✅" in result else ("#FF4444" if "⚠️" in result else "#FF6B6B")
        self.status_label.configure(text=result, text_color=color)
        self.last_update_label.configure(text=f"Last update: {config.last_update}")
        self.root.update()

    def clear_cache(self):
        if not os.path.exists(SAVE_DIR):
            messagebox.showinfo("Cache", "No folder found.")
            return
        if not messagebox.askyesno("Clear Cache", "Keep only the last 5 images?"):
            return

        files = sorted([os.path.join(SAVE_DIR, f) for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')],
                       key=os.path.getmtime, reverse=True)
        deleted = 0
        for f in files[5:]:
            try:
                os.remove(f)
                deleted += 1
            except:
                pass
        messagebox.showinfo("Cache", f"{deleted} old image(s) deleted.")

    # ---------- Auto Update ----------
    def toggle_auto_update(self):
        if self.schedule_running:
            self.stop_schedule()
        else:
            self.start_schedule()

    def start_schedule(self):
        if self.schedule_running:
            return

        hours = 4
        config.interval_hours = hours
        config.save()

        self.schedule_running = True
        self.auto_btn.configure(text="⏹ Stop Auto", fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])

        def run():
            schedule.clear()
            schedule.every(hours).hours.do(self.scheduled_job)
            while self.schedule_running:
                schedule.run_pending()
                time.sleep(30)

        self.schedule_thread = threading.Thread(target=run, daemon=True)
        self.schedule_thread.start()

    def stop_schedule(self):
        self.schedule_running = False
        self.auto_btn.configure(text="⏰ Auto Update (4h)", fg_color=COLORS["success"], hover_color="#1B5E20")
        config.interval_hours = 0
        config.save()

    def scheduled_job(self):
        self.root.after(0, lambda: self.status_label.configure(text="⏳ Auto-updating...", text_color="#FFB74D"))
        def do():
            result = update_wallpaper()
            self.root.after(0, lambda: self.after_update(result))
        threading.Thread(target=do, daemon=True).start()

    def on_close(self):
        self.schedule_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

# ========== Run ==========
config = Config()
if __name__ == "__main__":
    try:
        app = NASAApp()
        app.run()
    except Exception as e:
        # Silent fail - no input() in exe version
        pass