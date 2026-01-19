import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, Image, ImageTk
import easyocr
import numpy as np
from deep_translator import GoogleTranslator
import threading
import time
import keyboard
import sys
import win32gui
import win32con
import os
import webbrowser 
import requests 
import ctypes # YENİ: Görev çubuğu ikonu için gerekli

# --- GOSHAWK EYE v1.1 ---
# Final Release (Icon Fixed)
# Fix: Added AppUserModelID to force Windows Taskbar icon.
# Fix: Applied iconbitmap to the visible 'menu' window, not just the hidden 'root'.

CURRENT_VERSION = "1.1" 
VERSION_URL = "https://aoe4labs.com/version.txt" 

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- DİL AYARLARI ---
LANGUAGES = {
    "English":    ("en", "en"),
    "Turkish":    ("tr", "tr"),
    "German":     ("de", "de"),
    "French":     ("fr", "fr"),
    "Spanish":    ("es", "es"),
    "Russian":    ("ru", "ru"),
    "Italian":    ("it", "it"),
    "Portuguese": ("pt", "pt"),         
    "Chinese":    ("ch_sim", "zh-CN")   
}

# --- GÖRSEL AYARLAR ---
COLORS = {
    "Yellow":           "yellow",
    "Cyan":             "#00cec9",
    "Green":            "#55efc4",
    "White":            "white",
    "Orange":           "#ff7675",
    "Black":            "#050505"
}

FONT_SIZES = ["10", "12", "14", "16", "18", "20", "22", "24"]

class AlanSecici:
    def __init__(self, master_root):
        self.top = tk.Toplevel(master_root)
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)
        self.top.configure(background='black')
        self.top.attributes("-topmost", True)
        
        # İkonu buraya da ekleyelim (Garanti olsun)
        try: self.top.iconbitmap(resource_path("logo.ico"))
        except: pass
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.selected_area = None

        self.canvas = tk.Canvas(self.top, cursor="cross", bg="grey10", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_text(
            self.top.winfo_screenwidth() // 2, 
            self.top.winfo_screenheight() // 2, 
            text="GOSHAWK EYE: SELECT SUBTITLE AREA\n(ESC: Cancel Selection)", 
            fill="#00ffea", font=("Segoe UI", 20, "bold"), justify="center"
        )

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.top.bind("<Escape>", self.iptal_et)
        self.canvas.bind("<Escape>", self.iptal_et)
        
        self.top.wait_visibility()
        self.top.focus_force()
        self.top.grab_set()
        self.top.wait_window(self.top)

    def iptal_et(self, event=None):
        self.selected_area = None
        self.top.destroy()

    def on_button_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='#00ff00', width=2)

    def on_move_press(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        if (x2 - x1) > 20:
            self.selected_area = (x1, y1, x2, y2)
            self.top.destroy()

class EkranCevirici:
    def __init__(self, root, ocr_code, trans_src, trans_trg, text_color, font_size):
        self.root = root
        self.root.title(f"GosHawK Eye v{CURRENT_VERSION}") 
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.wm_attributes("-transparentcolor", "black")
        
        # Ana pencereye ikonu zorla
        try:
            self.root.iconbitmap(resource_path("logo.ico"))
        except: pass

        self.scan_region = None
        self.aktif = False
        self.son_ceviri = "" 
        
        self.min_width = 400 
        self.current_width = 100
        self.win_x = 0
        
        self.ocr_code = ocr_code
        self.text_color = text_color
        self.font_size = font_size

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        font_style = ("Segoe UI", self.font_size, "bold")
        
        self.text_shadow = self.canvas.create_text(10, 10, text="", font=font_style, fill="black", anchor="nw")
        self.text_main = self.canvas.create_text(10, 10, text="", font=font_style, fill=self.text_color, anchor="nw")
        
        print(f"Engine Loaded: {ocr_code} -> {trans_trg} | Color: {text_color} | Size: {font_size}")
        
        self.reader = easyocr.Reader([self.ocr_code], gpu=False) 
        self.translator = GoogleTranslator(source=trans_src, target=trans_trg)

        keyboard.add_hotkey('F2', self.toggle_ceviri)
        keyboard.add_hotkey('F3', self.yeni_secim_tetikle)
        keyboard.add_hotkey('End', self.kapat)
        
        self.running = True
        self.thread = threading.Thread(target=self.cevir_threadi, daemon=True)
        self.thread.start()
        
        self.arayuz_guncelle()

    def hayalet_modu_aktif_et(self):
        try:
            hwnd = win32gui.GetParent(self.root.winfo_id())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE)
        except: pass

    def arayuz_yaz(self, metin, renk):
        text_width_limit = self.current_width - 20
        font_style = ("Segoe UI", self.font_size, "bold")

        shadow_color = "white" if self.text_color == "#050505" else "black"

        self.canvas.itemconfig(self.text_shadow, text=metin, width=text_width_limit, font=font_style, fill=shadow_color)
        self.canvas.coords(self.text_shadow, 12, 12)
        
        final_color = "green" if metin == "Scanning..." else (renk if renk != "yellow" else self.text_color)
        
        self.canvas.itemconfig(self.text_main, text=metin, fill=final_color, width=text_width_limit, font=font_style)
        self.canvas.coords(self.text_main, 10, 10)
        
        bbox = self.canvas.bbox(self.text_main)
        if bbox and self.scan_region:
            text_height = bbox[3] - bbox[1]
            new_height = max(text_height + 40, 80)
            
            sel_x1, sel_y1, sel_x2, sel_y2 = self.scan_region
            
            target_y = sel_y1 - new_height - 10
            
            if target_y < 0:
                target_y = sel_y2 + 10 
                
            self.root.geometry(f"{self.current_width}x{new_height}+{self.win_x}+{target_y}")

    def konumlandir(self, bolge):
        self.scan_region = bolge
        selection_width = bolge[2] - bolge[0]
        self.current_width = max(selection_width, self.min_width)
        self.win_x = bolge[0]
        
        self.root.geometry(f"{self.current_width}x80+{self.win_x}+{bolge[1]-100}")
        self.arayuz_yaz("GOSHAWK EYE READY: [F2] START", "white")
        self.root.deiconify()
        self.root.after(100, self.hayalet_modu_aktif_et)

    def yeni_secim_tetikle(self): self.root.after(0, self.yeniden_secim_yap)

    def yeniden_secim_yap(self):
        self.aktif = False 
        self.root.withdraw() 
        secici = AlanSecici(self.root)
        if secici.selected_area:
            self.konumlandir(secici.selected_area)
        else:
            self.root.deiconify()
            self.root.after(100, self.hayalet_modu_aktif_et)

    def arayuz_guncelle(self):
        if not self.running: return
        try:
            hwnd = win32gui.GetParent(self.root.winfo_id())
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        except: pass

        if self.aktif:
            if self.son_ceviri: self.arayuz_yaz(self.son_ceviri, self.text_color)
            else: self.arayuz_yaz("Scanning...", "green")
        else:
            self.arayuz_yaz(f"PAUSED [F2]", "red")
        self.root.after(200, self.arayuz_guncelle)

    def toggle_ceviri(self):
        self.aktif = not self.aktif
        if self.aktif: self.son_ceviri = ""

    def cevir_threadi(self):
        onceki_yazi = "" 
        while self.running:
            if self.aktif and self.scan_region:
                try:
                    img = ImageGrab.grab(bbox=self.scan_region)
                    result = self.reader.readtext(np.array(img), detail=0, paragraph=True)
                    text = " ".join(result).strip()
                    if len(text) > 1 and text != onceki_yazi:
                        self.son_ceviri = self.translator.translate(text)
                        onceki_yazi = text
                except: pass
                time.sleep(0.1) 
            else: time.sleep(0.5)

    def kapat(self):
        self.running = False
        self.root.destroy()
        sys.exit()

def create_hover_button(parent, text, command, bg_color="#0984e3", hover_color="#00cec9", fg_color="white", font=("Segoe UI", 12, "bold"), padx=20, pady=10):
    btn = tk.Button(parent, text=text, bg=bg_color, fg=fg_color, font=font, command=command, cursor="hand2", borderwidth=0, padx=padx, pady=pady)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_color))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg_color))
    return btn

def main():
    # --- 1. GÖREV ÇUBUĞU İKONU ÇÖZÜMÜ (APP ID) ---
    try:
        # Windows'a "Ben sıradan bir Python scripti değilim, ben GosHawK Eye'ım" diyoruz.
        myappid = 'aoe4labs.goshawkeye.tool.v1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except: pass

    root = tk.Tk()
    root.withdraw() # Ana pencereyi gizle

    # --- 2. İKON ATAMA (HEM ROOT HEM MENÜ İÇİN) ---
    try:
        icon_path = resource_path("logo.ico")
        root.iconbitmap(icon_path) # Root'a ata (Arka plan için)
    except: pass

    menu = tk.Toplevel(root)
    menu.title(f"GosHawK Eye v{CURRENT_VERSION}") 
    menu.geometry('500x620') 
    
    # --- 3. GÖRÜNÜR PENCEREYE İKONU ZORLA ---
    try:
        menu.iconbitmap(icon_path)
    except: pass
    
    bg_dark = "#2d3436"
    bg_frame = "#353b48"
    accent_color = "#00cec9"
    menu.configure(bg=bg_dark)

    x = (menu.winfo_screenwidth()/2) - 250
    y = (menu.winfo_screenheight()/2) - 310 
    menu.geometry('+%d+%d' % (x, y))

    logo_frame = tk.Frame(menu, bg=bg_dark)
    logo_frame.pack(pady=(25, 5))

    tk.Label(logo_frame, text="◎", font=("Segoe UI Symbol", 50), fg=accent_color, bg=bg_dark).pack(side="left", padx=5)
    title_label = tk.Label(logo_frame, text="GOSHAWK EYE", font=("Segoe UI Black", 26, "bold"), fg="white", bg=bg_dark)
    title_label.pack(side="left")

    tk.Label(menu, text=f"v{CURRENT_VERSION}", font=("Segoe UI", 10, "italic"), fg="#dfe6e9", bg=bg_dark).pack(pady=(0, 10))

    # --- AYARLAR ---
    settings_frame = tk.Frame(menu, bg=bg_frame, padx=15, pady=15)
    settings_frame.pack(fill="x", padx=40, pady=5)

    tk.Label(settings_frame, text="TRANSLATION SETTINGS", font=("Segoe UI", 10, "bold"), bg=bg_frame, fg="white").pack(pady=(0,10))

    grid_frame = tk.Frame(settings_frame, bg=bg_frame)
    grid_frame.pack(fill="x")

    grid_frame.grid_columnconfigure(0, weight=1)
    grid_frame.grid_columnconfigure(1, weight=1)
    grid_frame.grid_columnconfigure(2, weight=1) 
    grid_frame.grid_columnconfigure(3, weight=1)
    grid_frame.grid_columnconfigure(4, weight=1)

    source_var = tk.StringVar(menu)
    target_var = tk.StringVar(menu)
    color_var = tk.StringVar(menu)
    size_var = tk.StringVar(menu)

    source_var.set("English") 
    target_var.set("Turkish") 
    color_var.set("Yellow") 
    size_var.set("12")

    tk.Label(grid_frame, text="Source:", font=("Segoe UI", 9), bg=bg_frame, fg="#dfe6e9").grid(row=0, column=0, sticky="w")
    source_menu = tk.OptionMenu(grid_frame, source_var, *LANGUAGES.keys())
    source_menu.config(bg="#636e72", fg="white", width=9, highlightthickness=0, borderwidth=0)
    source_menu["menu"].config(bg="#636e72", fg="white")
    source_menu.grid(row=0, column=1, sticky="w", pady=5)

    tk.Label(grid_frame, text="Target:", font=("Segoe UI", 9), bg=bg_frame, fg="#dfe6e9").grid(row=1, column=0, sticky="w")
    target_menu = tk.OptionMenu(grid_frame, target_var, *LANGUAGES.keys())
    target_menu.config(bg="#636e72", fg="white", width=9, highlightthickness=0, borderwidth=0)
    target_menu["menu"].config(bg="#636e72", fg="white")
    target_menu.grid(row=1, column=1, sticky="w", pady=5)

    tk.Frame(grid_frame, bg=bg_frame, width=20).grid(row=0, column=2, rowspan=2)

    tk.Label(grid_frame, text="Color:", font=("Segoe UI", 9), bg=bg_frame, fg="#b2bec3").grid(row=0, column=3, sticky="w")
    color_menu = tk.OptionMenu(grid_frame, color_var, *COLORS.keys())
    color_menu.config(bg="#636e72", fg="white", width=9, highlightthickness=0, borderwidth=0)
    color_menu["menu"].config(bg="#636e72", fg="white")
    color_menu.grid(row=0, column=4, sticky="w", pady=5)

    tk.Label(grid_frame, text="Size:", font=("Segoe UI", 9), bg=bg_frame, fg="#b2bec3").grid(row=1, column=3, sticky="w")
    size_menu = tk.OptionMenu(grid_frame, size_var, *FONT_SIZES)
    size_menu.config(bg="#636e72", fg="white", width=9, highlightthickness=0, borderwidth=0)
    size_menu["menu"].config(bg="#636e72", fg="white")
    size_menu.grid(row=1, column=4, sticky="w", pady=5)

    frame_border = tk.Frame(menu, bg=accent_color, padx=2, pady=2)
    frame_border.pack(fill="x", padx=40, pady=(10, 0)) 
    frame_inner = tk.Frame(frame_border, bg=bg_frame, padx=10, pady=10)
    frame_inner.pack(fill="x")
    
    shortcuts = "HOTKEYS:\n[F2] Start / Pause\n[F3] Select New Area\n[End] Exit Application"
    tk.Label(frame_inner, text=shortcuts, font=("Consolas", 11, "bold"), bg=bg_frame, fg="white").pack()

    # --- UPDATE CHECKER ---
    def check_for_updates():
        try:
            nocache_url = f"{VERSION_URL}?t={int(time.time())}"
            response = requests.get(nocache_url, timeout=3)
            
            if response.status_code == 200:
                latest_version = response.text.strip()
                if latest_version > CURRENT_VERSION:
                    update_btn.pack(pady=10, before=start_btn)
        except: pass

    def open_site(e=None):
        webbrowser.open("https://aoe4labs.com/translator.html")

    def show_info():
        info = tk.Toplevel(menu)
        info.title("System Info & Tips")
        try:
            info.iconbitmap(resource_path("logo.ico"))
        except: pass
        
        info.geometry("400x450")
        info.configure(bg=bg_dark)
        ix = (info.winfo_screenwidth()/2) - 200
        iy = (info.winfo_screenheight()/2) - 225
        info.geometry('+%d+%d' % (ix, iy))
        
        # --- DETAYLI BİLGİ EKRANI ---
        info_text = f"""
        VERSION: {CURRENT_VERSION}
        
⚠️ PERFORMANCE & STARTUP ⚠️
This application uses Advanced AI (Deep Learning).
• High CPU usage & Fan noise is NORMAL.
• FIRST LAUNCH may take 15-20 seconds. 
  Please be patient!

DISPLAY MODE:
• Works best in 'Borderless Window'.
• Also supports Fullscreen (Z-Order Force).

SYSTEM REQUIREMENTS:
• CPU: Modern i5 / Ryzen 5 or better
• RAM: 8GB minimum

TIPS:
1. Select ONLY the subtitle text area.
2. Use [F2] to PAUSE during heavy combat.
        """
        tk.Label(info, text=info_text, font=("Segoe UI", 10), bg=bg_dark, fg="#dfe6e9", justify="left", padx=20, pady=20).pack(fill="both", expand=True)
        create_hover_button(info, "CLOSE", info.destroy, bg_color="#d63031", hover_color="#ff7675").pack(pady=10)

    def baslat():
        src_name = source_var.get()
        trg_name = target_var.get()
        color_name = color_var.get()
        size_val = int(size_var.get())
        
        ocr_code = LANGUAGES[src_name][0]     
        trans_src = LANGUAGES[src_name][1]    
        trans_trg = LANGUAGES[trg_name][1]
        selected_color_code = COLORS[color_name]
        
        menu.destroy()
        s = AlanSecici(root)
        if s.selected_area:
            app = EkranCevirici(root, ocr_code, trans_src, trans_trg, selected_color_code, size_val)
            app.konumlandir(s.selected_area)
            app.root.mainloop()
        else: sys.exit()

    # --- BUTONLAR ---
    
    update_btn = create_hover_button(menu, "✨ NEW UPDATE AVAILABLE! ✨", open_site, bg_color="#e17055", hover_color="#ff7675")
    
    start_btn = create_hover_button(menu, "START HUNTING", baslat, bg_color="#0984e3", hover_color=accent_color)
    start_btn.pack(pady=(15, 10))
    
    info_btn = create_hover_button(menu, "SYSTEM INFO & TIPS", show_info, bg_color="#636e72", hover_color="#b2bec3", font=("Segoe UI", 10))
    info_btn.pack(pady=5)

    # --- BANNER ---
    try:
        img_path = resource_path("aoe4labs_banner.png")
        original = Image.open(img_path).convert("RGBA")
        width = 200 
        height = int((width / original.width) * original.height)
        resized = original.resize((width, height), Image.Resampling.LANCZOS)
        banner_img = ImageTk.PhotoImage(resized)

        banner_label = tk.Label(menu, image=banner_img, bg=bg_dark, cursor="hand2")
        banner_label.image = banner_img 
        
        banner_label.bind("<Button-1>", open_site)
        banner_label.pack(side="bottom", pady=(15, 20)) 
    except Exception as e:
        link_lbl = tk.Label(menu, text="Visit Official Home: aoe4labs.com", font=("Segoe UI", 10, "underline"), fg="#74b9ff", bg=bg_dark, cursor="hand2")
        link_lbl.pack(side="bottom", pady=15)
        link_lbl.bind("<Button-1>", open_site)

    threading.Thread(target=check_for_updates, daemon=True).start()

    root.mainloop()

if __name__ == "__main__":
    main()
