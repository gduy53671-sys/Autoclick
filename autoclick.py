"""
Auto Clicker Tool - Floating Button
====================================
Nút nổi trên mọi ứng dụng, có menu tùy chỉnh tốc độ.

Hotkeys:
    F8  - Chọn vị trí click (tại vị trí chuột hiện tại)
    F9  - Bật / Tắt auto click
    F10 - Ẩn / Hiện nút
    ESC - Thoát tool

Tác giả: AI Assistant
"""

import tkinter as tk
from tkinter import messagebox
import pyautogui
import threading
import time
import json
import os
import sys

# Tắt failsafe mặc định để không bị crash giữa chừng (dùng hotkey thay thế)
pyautogui.FAILSAFE = False

# ============================================================
# CẤU HÌNH
# ============================================================
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".auto_clicker_config.json")

COLORS = {
    "bg_dark":    "#0f1626",
    "bg_menu":    "#1e3c72",
    "bg_panel":   "#2a5298",
    "accent":     "#38ef7d",
    "accent2":    "#11998e",
    "danger":     "#ff6a00",
    "text":       "#ffffff",
    "text_dim":   "#cdd9ff",
    "text_muted": "#8899cc",
}

DEFAULT_CONFIG = {
    "cps": 10,
    "mode": "fixed",       # "fixed" hoặc "cursor"
    "click_x": None,
    "click_y": None,
    "button_x": 200,
    "button_y": 200,
}


# ============================================================
# CLASS CHÍNH
# ============================================================
class AutoClickerApp:
    def __init__(self):
        # ---- State ----
        self.config = self.load_config()
        self.clicking = False
        self.thread = None
        self.drag_data = {"x": 0, "y": 0, "moved": False}
        self.menu_open = False

        # ---- Cửa sổ chính (nút nổi) ----
        self.root = tk.Tk()
        self.root.title("AutoClicker")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.geometry(f"70x70+{self.config['button_x']}+{self.config['button_y']}")
        self.root.configure(bg=COLORS["bg_dark"])

        # Nút nổi (dùng Label để tự vẽ đẹp hơn Button)
        self.float_btn = tk.Label(
            self.root,
            text="🖱️",
            font=("Segoe UI Emoji", 26),
            bg=COLORS["bg_dark"],
            fg=COLORS["text"],
            cursor="hand2",
        )
        self.float_btn.pack(fill="both", expand=True)

        # Sự kiện kéo thả & click
        self.float_btn.bind("<Button-1>", self.on_press)
        self.float_btn.bind("<B1-Motion>", self.on_drag)
        self.float_btn.bind("<ButtonRelease-1>", self.on_release)
        self.float_btn.bind("<Button-3>", lambda e: self.quit_app())  # chuột phải để thoát

        # ---- Menu popup ----
        self.menu = tk.Toplevel(self.root)
        self.menu.overrideredirect(True)
        self.menu.attributes("-topmost", True)
        self.menu.configure(bg=COLORS["bg_menu"])
        self.menu.withdraw()
        self.build_menu()

        # ---- Hotkeys toàn cục (dùng keyboard module nếu có) ----
        self.setup_hotkeys()

        # ---- Bắt đầu vòng lặp ----
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()

    # ========================================================
    # CẤU HÌNH - LƯU / ĐỌC
    # ========================================================
    def load_config(self):
        cfg = DEFAULT_CONFIG.copy()
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                cfg.update(saved)
        except Exception:
            pass
        return cfg

    def save_config(self):
        try:
            self.config["button_x"] = self.root.winfo_x()
            self.config["button_y"] = self.root.winfo_y()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    # ========================================================
    # XÂY DỰNG MENU POPUP
    # ========================================================
    def build_menu(self):
        frame = tk.Frame(self.menu, bg=COLORS["bg_menu"], padx=16, pady=14)
        frame.pack()

        # Tiêu đề
        tk.Label(
            frame, text="⚡ Auto Clicker",
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["bg_menu"], fg=COLORS["text"],
        ).pack(anchor="w")

        # ----- Tốc độ -----
        tk.Label(
            frame, text="Tốc độ (click/giây):",
            font=("Segoe UI", 9),
            bg=COLORS["bg_menu"], fg=COLORS["text_dim"],
        ).pack(anchor="w", pady=(10, 2))

        speed_row = tk.Frame(frame, bg=COLORS["bg_menu"])
        speed_row.pack(fill="x")

        self.cps_var = tk.IntVar(value=self.config["cps"])
        self.cps_label = tk.Label(
            speed_row, text=str(self.config["cps"]),
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["bg_menu"], fg=COLORS["accent"],
        )
        self.cps_label.pack(side="right")

        tk.Scale(
            speed_row,
            from_=1, to=100,
            orient="horizontal",
            variable=self.cps_var,
            command=self.on_speed_change,
            bg=COLORS["bg_menu"],
            fg=COLORS["text"],
            troughcolor=COLORS["bg_panel"],
            highlightthickness=0, bd=0,
            length=180,
            activebackground=COLORS["accent"],
            showvalue=False,
        ).pack(side="left", fill="x", expand=True)

        # ----- Chế độ click -----
        tk.Label(
            frame, text="Chế độ:",
            font=("Segoe UI", 9),
            bg=COLORS["bg_menu"], fg=COLORS["text_dim"],
        ).pack(anchor="w", pady=(8, 2))

        self.mode_var = tk.StringVar(value=self.config["mode"])

        tk.Radiobutton(
            frame, text="Click tại vị trí cố định (F8 để chọn)",
            variable=self.mode_var, value="fixed",
            command=self.on_mode_change,
            bg=COLORS["bg_menu"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_menu"],
            activeforeground=COLORS["accent"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        tk.Radiobutton(
            frame, text="Click tại vị trí chuột hiện tại",
            variable=self.mode_var, value="cursor",
            command=self.on_mode_change,
            bg=COLORS["bg_menu"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_menu"],
            activeforeground=COLORS["accent"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        # Hiển thị vị trí đã chọn
        pos_text = "Vị trí: Chưa chọn (nhấn F8)"
        pos_color = COLORS["text_muted"]
        if self.config["click_x"] is not None:
            pos_text = f"Vị trí: ({self.config['click_x']}, {self.config['click_y']})"
            pos_color = COLORS["accent"]

        self.pos_label = tk.Label(
            frame, text=pos_text,
            font=("Segoe UI", 8),
            bg=COLORS["bg_menu"], fg=pos_color,
        )
        self.pos_label.pack(anchor="w", pady=(4, 8))

        # ----- Nút Start/Stop -----
        self.toggle_btn = tk.Button(
            frame, text="▶ BẮT ĐẦU  (F9)",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["accent"], fg=COLORS["bg_dark"],
            bd=0, cursor="hand2", relief="flat",
            activebackground=COLORS["accent2"],
            activeforeground=COLORS["text"],
            command=self.toggle_clicking,
            padx=20, pady=8,
        )
        self.toggle_btn.pack(fill="x", pady=(4, 4))

        # ----- Nút reset vị trí -----
        tk.Button(
            frame, text="↺ Xóa vị trí đã chọn",
            font=("Segoe UI", 8),
            bg=COLORS["bg_panel"], fg=COLORS["text"],
            bd=0, cursor="hand2", relief="flat",
            activebackground=COLORS["bg_dark"],
            activeforeground=COLORS["text"],
            command=self.reset_position,
            pady=4,
        ).pack(fill="x")

        # ----- Hướng dẫn -----
        tk.Label(
            frame,
            text="F8: chọn vị trí  •  F9: chạy/dừng\nF10: ẩn/hiện  •  ESC: thoát",
            font=("Segoe UI", 7),
            bg=COLORS["bg_menu"], fg=COLORS["text_muted"],
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    # ========================================================
    # CALLBACK MENU
    # ========================================================
    def on_speed_change(self, val):
        cps = int(float(val))
        self.config["cps"] = cps
        self.cps_label.config(text=str(cps))
        self.save_config()

    def on_mode_change(self):
        self.config["mode"] = self.mode_var.get()
        self.save_config()

    def reset_position(self):
        self.config["click_x"] = None
        self.config["click_y"] = None
        self.pos_label.config(text="Vị trí: Chưa chọn (nhấn F8)", fg=COLORS["text_muted"])
        self.save_config()

    # ========================================================
    # KÉO THẢ NÚT NỔI
    # ========================================================
    def on_press(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["moved"] = False

    def on_drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        if abs(dx) > 3 or abs(dy) > 3:
            self.drag_data["moved"] = True

        nx = self.root.winfo_x() + dx
        ny = self.root.winfo_y() + dy
        self.root.geometry(f"+{nx}+{ny}")

        # Di chuyển menu theo nút
        if self.menu_open:
            self.update_menu_position()

    def on_release(self, event):
        if not self.drag_data["moved"]:
            # Click (không kéo) → mở/đóng menu
            self.toggle_menu()
        else:
            self.save_config()

    # ========================================================
    # MENU SHOW/HIDE
    # ========================================================
    def update_menu_position(self):
        bx, by = self.root.winfo_x(), self.root.winfo_y()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Mặc định menu hiện bên phải nút
        mx = bx + 80
        # Nếu tràn mép phải → hiện bên trái
        if mx + 260 > screen_w:
            mx = bx - 260
        # Nếu tràn mép trái → căn về 0
        if mx < 0:
            mx = 5

        # Nếu tràn mép dưới → kéo lên
        my = by
        if my + 400 > screen_h:
            my = max(5, screen_h - 410)

        self.menu.geometry(f"+{mx}+{my}")

    def toggle_menu(self):
        if self.menu_open:
            self.menu.withdraw()
            self.menu_open = False
        else:
            self.update_menu_position()
            self.menu.deiconify()
            self.menu.lift()
            self.menu.attributes("-topmost", True)
            self.menu_open = True

    # ========================================================
    # CLICK ENGINE
    # ========================================================
    def toggle_clicking(self):
        if self.clicking:
            self.stop_clicking()
        else:
            self.start_clicking()

    def start_clicking(self):
        mode = self.mode_var.get()
        target = None

        if mode == "fixed":
            if self.config["click_x"] is None:
                self.pos_label.config(text="⚠ Chưa chọn vị trí! Nhấn F8", fg=COLORS["danger"])
                return
            target = (self.config["click_x"], self.config["click_y"])

        self.clicking = True
        self.toggle_btn.config(
            text="■ DỪNG LẠI  (F9)",
            bg=COLORS["danger"], fg=COLORS["text"],
        )
        self.float_btn.config(bg=COLORS["accent2"])

        self.thread = threading.Thread(
            target=self.click_loop,
            args=(target, mode == "cursor"),
            daemon=True,
        )
        self.thread.start()

    def click_loop(self, target, live_cursor):
        """Vòng lặp click chạy trên thread riêng."""
        while self.clicking:
            try:
                if live_cursor:
                    pyautogui.click()
                else:
                    pyautogui.click(target[0], target[1])
            except Exception as e:
                print(f"[Click error] {e}")

            interval = 1.0 / max(1, self.config["cps"])
            # Ngủ theo từng bước nhỏ để phản hồi Stop nhanh
            slept = 0.0
            step = 0.01
            while slept < interval and self.clicking:
                time.sleep(min(step, interval - slept))
                slept += step

    def stop_clicking(self):
        self.clicking = False
        self.toggle_btn.config(
            text="▶ BẮT ĐẦU  (F9)",
            bg=COLORS["accent"], fg=COLORS["bg_dark"],
        )
        self.float_btn.config(bg=COLORS["bg_dark"])

    # ========================================================
    # HOTKEYS
    # ========================================================
    def setup_hotkeys(self):
        """Thử dùng thư viện keyboard (nếu có) để hotkey toàn cục.
        Nếu không có → fallback dùng hotkey khi cửa sổ có focus."""
        try:
            import keyboard

            keyboard.add_hotkey("f8",  lambda: self.root.after(0, self.set_position))
            keyboard.add_hotkey("f9",  lambda: self.root.after(0, self.toggle_clicking))
            keyboard.add_hotkey("f10", lambda: self.root.after(0, self.toggle_visibility))
            keyboard.add_hotkey("esc", lambda: self.root.after(0, self.quit_app))
            print("[OK] Đã bật hotkey toàn cục (F8 / F9 / F10 / ESC)")
        except ImportError:
            # Fallback: bind trên cửa sổ
            self.root.bind_all("<F8>",  lambda e: self.set_position())
            self.root.bind_all("<F9>",  lambda e: self.toggle_clicking())
            self.root.bind_all("<F10>", lambda e: self.toggle_visibility())
            self.root.bind_all("<Escape>", lambda e: self.quit_app())
            print("[!] Chưa cài 'keyboard' → hotkey chỉ hoạt động khi tool được focus.")
            print("    Cài thêm để hotkey toàn cục: pip install keyboard")

    def set_position(self):
        x, y = pyautogui.position()
        self.config["click_x"] = x
        self.config["click_y"] = y
        self.pos_label.config(text=f"Vị trí: ({x}, {y})", fg=COLORS["accent"])
        self.mode_var.set("fixed")
        self.config["mode"] = "fixed"
        self.save_config()

    def toggle_visibility(self):
        if self.root.state() == "withdrawn":
            self.root.deiconify()
        else:
            self.menu.withdraw()
            self.menu_open = False
            self.root.withdraw()

    # ========================================================
    # THOÁT
    # ========================================================
    def quit_app(self):
        self.clicking = False
        self.save_config()
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("  ⚡ AUTO CLICKER TOOL")
    print("=" * 55)
    print("  F8  : Chọn vị trí click (tại vị trí chuột)")
    print("  F9  : Bật / Tắt auto click")
    print("  F10 : Ẩn / Hiện nút nổi")
    print("  ESC : Thoát tool")
    print("  Chuột phải vào nút nổi: Thoát nhanh")
    print("=" * 55)

    try:
        AutoClickerApp()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
