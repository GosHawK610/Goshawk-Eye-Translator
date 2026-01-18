import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab
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

# --- GOSHAWK EYE v1.0 ---
# Final Release (Complete Edition)
# Includes: Auto-Fit, System Requirements Info, Multi-Language, Z-Order Fix

def resource_path(relative_path):
    """ EXE içindeki dosya yolunu bulur """
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

class AlanSecici:
    def __init__(self, master_root):
        self.top = tk.Toplevel(master_root)
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)
        self.top.configure(background='black')
        self.top.attributes("-topmost", True)
        
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
    def __init__(self, root, ocr_code, trans_src, trans_trg):
        self.root = root
        self.root.title("GosHawK Eye v1.0") 
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.wm_attributes("-transparentcolor", "black")
        
        try:
            self.root.iconbitmap(resource_path("logo.ico"))
        except: pass

        self.scan_region = None
        self.aktif = False
        self.son_ceviri = "" 
        
        # Pencere Boyut Değişkenleri
        self.win_x = 0
        self.win_y = 0
        self.min_width = 400 # En az 400px genişlik olacak
        self.current_width = 100
        
        self.ocr_code = ocr_code

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.text_shadow = self.canvas.create_text(10, 10, text="", font=("Segoe UI", 12, "bold"), fill="black", anchor="nw")
        self.text_main = self.canvas.create_text(10, 10, text="", font=("Segoe UI", 12, "bold"), fill="#00cec9", anchor="nw")
        
        print(f"GosHawK Eye v1.0: Loading Engine (OCR: {ocr_code} | TR: {trans_src}->{trans_trg})...")
        
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

    def arayuz_yaz(self, metin, renk="#00cec9"):
        # Yazı genişliği: Pencere genişliğinden biraz az olsun
        text_width_limit = self.current_width - 20
        
        # 1. Yazıyı güncelle
        self.canvas.itemconfig(self.text_shadow, text=metin, width=text_width_limit)
        self.canvas.coords(self.text_shadow, 12, 12)
        self.canvas.itemconfig(self.text_main, text=metin, fill=renk, width=text_width_limit)
        self.canvas.coords(self.text_main, 10, 10)
        
        # 2. Yazının kapladığı alanı hesapla (Otomatik Yükseklik)
        bbox = self.canvas.bbox(self.text_main)
        if bbox:
            text_height = bbox[3] - bbox[1]
            # Pencere yüksekliğini yazıya göre ayarla (+30px boşluk)
            new_height = max(text_height + 30, 80)
            self.root.geometry(f"{self.current_width}x{new_height}+{self.win_x}+{self.win_y}")

    def konumlandir(self, bolge):
        self.scan_region = bolge
        
        # Seçilen alanın genişliğini al
        selection_width = bolge[2] - bolge[0]
        
        # Eğer seçilen alan çok darsa, pencereyi GENİŞ tut (En az 400px)
        self.current_width = max(selection_width, self.min_width)
        
        self.win_x = bolge[0]
        self.win_y = max(bolge[1] - 80, 0)
        
        self.root.geometry(f"{self.current_width}x80+{self.win_x}+{self.win_y}")
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
            if self.son_ceviri: self.arayuz_yaz(self.son_ceviri, "yellow")
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
    root = tk.Tk()
    root.withdraw()

    try:
        root.iconbitmap(resource_path("logo.ico"))
    except: pass

    menu = tk.Toplevel(root)
    menu.title("GosHawK Eye v1.0") 
    menu.geometry('500x650') 
    
    try:
        menu.iconbitmap(resource_path("logo.ico"))
    except: pass
    
    bg_dark = "#2d3436"
    bg_frame = "#353b48"
    accent_color = "#00cec9"
    menu.configure(bg=bg_dark)
    
    x = (menu.winfo_screenwidth()/2) - 250
    y = (menu.winfo_screenheight()/2) - 325
    menu.geometry('+%d+%d' % (x, y))

    logo_frame = tk.Frame(menu, bg=bg_dark)
    logo_frame.pack(pady=(35, 10))

    tk.Label(logo_frame, text="◎", font=("Segoe UI Symbol", 50), fg=accent_color, bg=bg_dark).pack(side="left", padx=5)
    title_label = tk.Label(logo_frame, text="GOSHAWK EYE", font=("Segoe UI Black", 26, "bold"), fg="white", bg=bg_dark)
    title_label.pack(side="left")

    tk.Label(menu, text="v1.0 - Global Edition", font=("Segoe UI", 10, "italic"), fg="#dfe6e9", bg=bg_dark).pack(pady=(0, 10))

    # --- DİL SEÇİM ALANI ---
    lang_frame = tk.Frame(menu, bg=bg_frame, padx=10, pady=10)
    lang_frame.pack(fill="x", padx=40, pady=10)

    tk.Label(lang_frame, text="TRANSLATION SETTINGS", font=("Segoe UI", 10, "bold"), bg=bg_frame, fg="white").pack(pady=(0,5))

    # Değişkenler
    source_var = tk.StringVar(menu)
    target_var = tk.StringVar(menu)
    source_var.set("English") 
    target_var.set("Turkish") 

    # Kaynak Dil
    tk.Label(lang_frame, text="Game Language (Source):", font=("Segoe UI", 9), bg=bg_frame, fg="#dfe6e9").pack(anchor="w")
    source_menu = tk.OptionMenu(lang_frame, source_var, *LANGUAGES.keys())
    source_menu.config(bg="#636e72", fg="white", highlightthickness=0, borderwidth=0)
    source_menu["menu"].config(bg="#636e72", fg="white")
    source_menu.pack(fill="x", pady=(0, 10))

    # Hedef Dil
    tk.Label(lang_frame, text="Translate To (Target):", font=("Segoe UI", 9), bg=bg_frame, fg="#dfe6e9").pack(anchor="w")
    target_menu = tk.OptionMenu(lang_frame, target_var, *LANGUAGES.keys())
    target_menu.config(bg="#636e72", fg="white", highlightthickness=0, borderwidth=0)
    target_menu["menu"].config(bg="#636e72", fg="white")
    target_menu.pack(fill="x")

    # --- KISAYOL KUTUSU ---
    frame_border = tk.Frame(menu, bg=accent_color, padx=2, pady=2)
    frame_border.pack(fill="x", padx=40, pady=(10, 0))
    frame_inner = tk.Frame(frame_border, bg=bg_frame, padx=10, pady=10)
    frame_inner.pack(fill="x")
    
    shortcuts = "HOTKEYS:\n[F2] Start / Pause\n[F3] Select New Area\n[End] Exit Application"
    tk.Label(frame_inner, text=shortcuts, font=("Consolas", 11, "bold"), bg=bg_frame, fg="white").pack()

    def show_info():
        info = tk.Toplevel(menu)
        info.title("System Info & Tips")
        try:
            info.iconbitmap(resource_path("logo.ico"))
        except: pass
        info.geometry("400x450") # Pencere boyutu arttırıldı (Sığsın diye)
        info.configure(bg=bg_dark)
        ix = (info.winfo_screenwidth()/2) - 200
        iy = (info.winfo_screenheight()/2) - 225
        info.geometry('+%d+%d' % (ix, iy))
        
        info_text = """
⚠️ PERFORMANCE & STARTUP ⚠️
This application uses Advanced AI (Deep Learning).
• High CPU usage is NORMAL.
• Selecting 'Chinese' or other new languages 
  will trigger a download on first use.

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
        
        ocr_code = LANGUAGES[src_name][0]     
        trans_src = LANGUAGES[src_name][1]    
        trans_trg = LANGUAGES[trg_name][1]    
        
        menu.destroy()
        s = AlanSecici(root)
        if s.selected_area:
            app = EkranCevirici(root, ocr_code, trans_src, trans_trg)
            app.konumlandir(s.selected_area)
            app.root.mainloop()
        else: sys.exit()

    start_btn = create_hover_button(menu, "START HUNTING", baslat, bg_color="#0984e3", hover_color=accent_color)
    start_btn.pack(pady=(20, 10))
    info_btn = create_hover_button(menu, "SYSTEM INFO & TIPS", show_info, bg_color="#636e72", hover_color="#b2bec3", font=("Segoe UI", 10))
    info_btn.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()