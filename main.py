"""
LoL Auto-Accept - Modern UI
Beautiful gradient design with smooth animations
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyautogui
import time
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageFilter
import psutil


class ModernStyle:
    """Modern color palette and styling"""
    COLORS = {
        'primary': '#6366f1',       # Indigo
        'primary_hover': '#4f46e5',
        'secondary': '#ec4899',     # Pink
        'accent': '#10b981',        # Emerald
        'bg_dark': '#0f172a',       # Slate 900
        'bg_card': '#1e293b',       # Slate 800
        'text_main': '#f8fafc',     # Slate 50
        'text_dim': '#94a3b8',      # Slate 400
        'danger': '#ef4444',        # Red
        'warning': '#f59e0b',       # Amber
        'success': '#10b981',       # Emerald
    }
    
    @staticmethod
    def style_tk(root):
        """Apply modern styling to tkinter"""
        root.configure(bg=ModernStyle.COLORS['bg_dark'])
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Button styles
        style.configure(
            'Modern.TButton',
            background=ModernStyle.COLORS['primary'],
            foreground=ModernStyle.COLORS['text_main'],
            font=('Segoe UI', 10, 'bold'),
            borderwidth=0,
            focuscolor='none'
        )
        style.map('Modern.TButton',
            background=[('active', ModernStyle.COLORS['primary_hover'])],
            foreground=[('active', ModernStyle.COLORS['text_main'])]
        )
        
        # Label styles
        style.configure(
            'Title.TLabel',
            background=ModernStyle.COLORS['bg_dark'],
            foreground=ModernStyle.COLORS['text_main'],
            font=('Segoe UI', 18, 'bold')
        )
        style.configure(
            'Subtitle.TLabel',
            background=ModernStyle.COLORS['bg_dark'],
            foreground=ModernStyle.COLORS['text_dim'],
            font=('Segoe UI', 9)
        )
        style.configure(
            'Status.TLabel',
            background=ModernStyle.COLORS['bg_card'],
            foreground=ModernStyle.COLORS['text_main'],
            font=('Segoe UI', 10),
            padding=10,
            borderwidth=0,
            relief='flat'
        )
        
        # Frame styles
        style.configure(
            'Card.TFrame',
            background=ModernStyle.COLORS['bg_card'],
            relief='flat'
        )
        
        # Checkbutton styles
        style.configure(
            'Modern.TCheckbutton',
            background=ModernStyle.COLORS['bg_dark'],
            foreground=ModernStyle.COLORS['text_main'],
            font=('Segoe UI', 9)
        )


class LoLAutoAcceptApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LoL Auto-Accept")
        self.root.geometry("480x560")
        self.root.resizable(False, False)
        
        # Apply modern style
        ModernStyle.style_tk(root)
        
        # App state
        self.is_running = False
        self.image_path = None
        self.template_gray = None
        self.template_size = None
        self._stop_event = threading.Event()
        self.monitor_thread = None
        self.lol_window = None
        
        # Set window icon (placeholder - Windows will use default)
        self.root.iconbitmap(default='')
        
        # Create main container with gradient background
        self.create_gradient_background()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_gradient_background(self):
        """Create a gradient background effect"""
        self.bg_frame = tk.Frame(self.root, bg=ModernStyle.COLORS['bg_dark'])
        self.bg_frame.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Create gradient canvas
        self.canvas = tk.Canvas(self.bg_frame, bg=ModernStyle.COLORS['bg_dark'], 
                               highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.update_gradient()
        
        self.root.bind('<Configure>', lambda e: self.update_gradient())

    def update_gradient(self):
        """Update gradient background"""
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        self.canvas.delete("gradient")
        
        # Create vertical gradient
        for i in range(height):
            ratio = i / height
            r1, g1, b1 = int(ModernStyle.COLORS['bg_dark'][1:3], 16), \
                        int(ModernStyle.COLORS['bg_dark'][3:5], 16), \
                        int(ModernStyle.COLORS['bg_dark'][5:7], 16)
            r2, g2, b2 = 30, 41, 59  # Slate 800
            
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            self.canvas.create_line(0, i, width, i, fill=color, tags="gradient")

    def setup_ui(self):
        """Create modern UI components"""
        # Title section
        title_frame = tk.Frame(self.root, bg=ModernStyle.COLORS['bg_dark'])
        title_frame.pack(pady=(30, 10))
        
        tk.Label(
            title_frame,
            text="⚡ LoL Auto-Accept",
            font=('Segoe UI', 20, 'bold'),
            fg=ModernStyle.COLORS['text_main'],
            bg=ModernStyle.COLORS['bg_dark']
        ).pack()
        
        tk.Label(
            title_frame,
            text="Smart scanning • Template matching • Auto-click",
            font=('Segoe UI', 9),
            fg=ModernStyle.COLORS['text_dim'],
            bg=ModernStyle.COLORS['bg_dark']
        ).pack(pady=5)

        # Main card container
        card = tk.Frame(self.root, bg=ModernStyle.COLORS['bg_card'],
                       highlightbackground=ModernStyle.COLORS['primary'],
                       highlightthickness=1)
        card.pack(padx=20, pady=10, fill='x', ipadx=10, ipady=10)
        
        # Image upload section
        upload_frame = tk.Frame(card, bg=ModernStyle.COLORS['bg_card'])
        upload_frame.pack(pady=15, padx=15, fill='x')
        
        tk.Label(
            upload_frame,
            text="📋 Accept Button Template",
            font=('Segoe UI', 9, 'bold'),
            fg=ModernStyle.COLORS['text_dim'],
            bg=ModernStyle.COLORS['bg_card']
        ).pack(anchor='w')
        
        # Image preview frame - no borders
        self.image_frame = tk.Frame(
            upload_frame,
            bg=ModernStyle.COLORS['bg_card'],
        )
        self.image_frame.pack(pady=(5, 2), fill='x')
        
        # Canvas - exact 300x80, fills frame
        self.image_canvas = tk.Canvas(
            self.image_frame,
            bg=ModernStyle.COLORS['bg_card'],
            width=300,
            height=80,
            highlightthickness=0
        )
        self.image_canvas.pack(fill='x', expand=True)
        
        # Placeholder - use anchor=center so coords are its center
        self.image_placeholder = self.image_canvas.create_text(
            0, 0,
            text="No template loaded",
            fill=ModernStyle.COLORS['text_dim'],
            font=('Segoe UI', 10),
            anchor='center'
        )
        # Recenter on canvas resize (and initial render)
        self.image_canvas.bind('<Configure>', self._on_canvas_configure)
        
        ttk.Button(
            upload_frame,
            text="📁 Browse Template",
            style='Modern.TButton'
        ).pack(pady=5, ipadx=10, ipady=5)
        
        # Update button command
        for btn in upload_frame.winfo_children():
            if isinstance(btn, ttk.Button):
                btn.configure(command=self.browse_image)
                btn.bind('<Enter>', lambda e: btn.configure(style='Modern.TButton'))
                btn.bind('<Leave>', lambda e: btn.configure(style='Modern.TButton'))
        # Also bind the browse button directly
        browse_btn = upload_frame.winfo_children()[-1]
        browse_btn.configure(command=self.browse_image)

        # Status display
        status_frame = tk.Frame(card, bg=ModernStyle.COLORS['bg_card'])
        status_frame.pack(pady=8, padx=15, fill='x')
        
        tk.Label(
            status_frame,
            text="📊 Current Status",
            font=('Segoe UI', 9, 'bold'),
            fg=ModernStyle.COLORS['text_dim'],
            bg=ModernStyle.COLORS['bg_card']
        ).pack(anchor='w')
        
        self.status_label = tk.Label(
            status_frame,
            text="💤 Ready to start",
            font=('Segoe UI', 10),
            fg=ModernStyle.COLORS['text_main'],
            bg=ModernStyle.COLORS['bg_card'],
            pady=8,
            padx=12,
            bd=0,
            relief='solid',
            highlightbackground=ModernStyle.COLORS['primary'],
            highlightthickness=2
        )
        self.status_label.pack(fill='x')

        # Controls
        control_frame = tk.Frame(card, bg=ModernStyle.COLORS['bg_card'])
        control_frame.pack(pady=8, padx=15)
        
        self.start_btn = ttk.Button(
            control_frame,
            text="▶ Start Scanning",
            style='Modern.TButton'
        )
        self.start_btn.pack(side='left', padx=5, ipadx=15, ipady=6)
        self.start_btn.configure(command=self.start_app)
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="⏹ Stop",
            style='Modern.TButton'
        )
        self.stop_btn.pack(side='left', padx=5, ipadx=15, ipady=6)
        self.stop_btn.configure(command=self.stop_app)
        self.stop_btn.configure(state=tk.DISABLED)

        # Info section
        info_frame = tk.Frame(self.root, bg=ModernStyle.COLORS['bg_dark'])
        info_frame.pack(pady=8)
        
        info_text = (
            "💡 Tip: Upload a clear screenshot of the accept button.\n"
            "✅ App will auto-detect and click when match found"
        )
        tk.Label(
            info_frame,
            text=info_text,
            font=('Segoe UI', 8),
            fg=ModernStyle.COLORS['text_dim'],
            bg=ModernStyle.COLORS['bg_dark'],
            justify='center'
        ).pack()

    def browse_image(self):
        """Open file dialog to select template image"""
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.bmp"),
            ("All files", "*.*")
        ]
        file_path = filedialog.askopenfilename(
            title="Select accept button image",
            filetypes=filetypes
        )
        
        if file_path:
            self.image_path = file_path
            try:
                img = Image.open(file_path)
                
                # Fix orientation issues
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    from PIL import ImageOps
                    img = ImageOps.exif_transpose(img)
                
                # Get actual canvas dimensions
                self.image_canvas.update_idletasks()
                canvas_width = self.image_canvas.winfo_width()
                canvas_height = self.image_canvas.winfo_height()
                
                # Scale to fit canvas while maintaining aspect ratio
                img_width, img_height = img.size
                if img_width == 0 or img_height == 0:
                    return
                
                scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized_img)
                
                # Clear previous image and show new one centered
                self.image_canvas.delete('all')
                x_center = canvas_width // 2
                y_center = canvas_height // 2
                self.image_canvas.create_image(x_center, y_center, anchor='center', image=photo)
                self.image_canvas.image = photo
                
                self._set_status("✅ Template loaded successfully", ModernStyle.COLORS['success'])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
                self._set_status("❌ Image load failed", ModernStyle.COLORS['danger'])

    def _on_canvas_configure(self, event):
        """Recenter placeholder whenever canvas resizes"""
        if self.image_placeholder:
            self.image_canvas.coords(
                self.image_placeholder,
                event.width // 2,
                event.height // 2
            )
    
    def _center_placeholder(self):
        """Recenter placeholder (convenience for external callers)"""
        if self.image_placeholder:
            w = self.image_canvas.winfo_width()
            h = self.image_canvas.winfo_height()
            self.image_canvas.coords(self.image_placeholder, w // 2, h // 2)
    
    def _set_status(self, text, color=None):
        """Update status with color"""
        if color:
            self.status_label.config(fg=color, highlightbackground=color)
        self.status_label.config(text=text)

    def _set_buttons(self, running):
        """Toggle button states"""
        self.start_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        
        if running:
            self.start_btn.config(text="⏳ Running...")
        else:
            self.start_btn.config(text="▶ Start Scanning")

    def _find_lol_window(self):
        """Find League of Legends window"""
        titles = [
            'League of Legends (Beta)',
            'League of Legends Client',
            'LeagueClientUx.exe',
            'League of Legends'
        ]
        
        for title in titles:
            windows = pyautogui.getAllWindows()
            for win in windows:
                if title in win.title:
                    return win
        
        # Fallback
        windows = pyautogui.getAllWindows()
        for win in windows:
            if 'league' in win.title.lower():
                return win
        
        return None

    def _is_lol_running(self):
        """Check if LeagueClientUx.exe is running"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'leagueclientux.exe' in proc.info['name'].lower():
                    return True
        except Exception:
            pass
        return False


    def _is_game_running(self):
        """Check if actual game (League of Legends.exe) is running"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and ('league of legends.exe' in proc.info['name'].lower() or
                                          'leagueoflegends.exe' in proc.info['name'].lower()):
                    return True
        except Exception:
            pass
        return False
    def start_app(self):
        """Start monitoring"""
        if not self.image_path:
            messagebox.showwarning("Warning", "Upload accept button image first!")
            return
        
        if self.is_running:
            messagebox.showinfo("Info", "Already running!")
            return

        # Load template
        try:
            pil_img = Image.open(self.image_path).convert('RGB')
            template = np.array(pil_img)
            
            if template.shape[0] > 300 or template.shape[1] > 300:
                scale = min(300 / template.shape[0], 300 / template.shape[1])
                template = cv2.resize(template, (
                    int(template.shape[1] * scale),
                    int(template.shape[0] * scale)
                ))
            
            self.template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
            self.template_size = self.template_gray.shape
        except Exception as e:
            messagebox.showerror("Error", f"Template load failed: {e}")
            return

        # Find LoL window
        self.lol_window = self._find_lol_window()
        if not self.lol_window:
            self._set_status("❌ LoL window not found", ModernStyle.COLORS['danger'])
            messagebox.showerror("Error", "League of Legends window not found!")
            return

        try:
            self.lol_window.activate()
            time.sleep(0.2)
        except Exception as e:
            self._set_status(f"⚠️ Window activate error", ModernStyle.COLORS['warning'])
            return

        try:
            self._lol_rect = (
                self.lol_window.left,
                self.lol_window.top,
                self.lol_window.width,
                self.lol_window.height
            )
        except Exception:
            self._lol_rect = None

        self.is_running = True
        self._stop_event.clear()
        self._set_status("🔍 Scanning LoL window...", ModernStyle.COLORS['primary'])
        self._set_buttons(True)

        self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()

    def stop_app(self):
        """Stop monitoring"""
        self.is_running = False
        self._stop_event.set()
        self.lol_window = None
        self._set_status("⏹ Stopped", ModernStyle.COLORS['text_dim'])
        self._set_buttons(False)

    def on_close(self):
        """Handle window close"""
        if self.is_running:
            self.stop_app()
        self.root.destroy()

    def _run_monitor(self):
        """Background monitoring thread"""
        while self.is_running and not self._stop_event.is_set():
            try:
                if not self._is_lol_running():
                    self._set_status("⚠️ LoL not running | Paused", ModernStyle.COLORS['warning'])
                    time.sleep(1)
                    continue

                # Don't scan if actual game is running
                if self._is_game_running():
                    self._set_status("🎮 Game detected | Waiting in queue...", ModernStyle.COLORS['warning'])
                    time.sleep(1)
                    continue

                if not self.lol_window or not self.lol_window.visible:
                    self.lol_window = self._find_lol_window()
                    if not self.lol_window:
                        self._set_status("⚠️ LoL window lost", ModernStyle.COLORS['warning'])
                        time.sleep(1)
                        continue
                    if not self.lol_window.visible:
                        self._set_status("⚠️ Client not visible | Waiting...", ModernStyle.COLORS['warning'])
                        time.sleep(1)
                        continue
                    try:
                        self._lol_rect = (
                            self.lol_window.left,
                            self.lol_window.top,
                            self.lol_window.width,
                            self.lol_window.height
                        )
                    except Exception:
                        pass

                # Scan only LoL window
                rect = self._lol_rect
                screenshot = pyautogui.screenshot(region=(rect[0], rect[1], rect[2], rect[3]))
                frame = np.array(screenshot)

                accept_pos = self.search_accept_button(frame)

                if accept_pos:
                    click_x = rect[0] + accept_pos[0]
                    click_y = rect[1] + accept_pos[1]
                    self._set_status("✅ ACCEPT FOUND! Clicking...", ModernStyle.COLORS['success'])
                    pyautogui.click(click_x, click_y)
                    self._stop_event.wait(3)
                else:
                    self._set_status("🔍 Scanning LoL window...", ModernStyle.COLORS['primary'])
                    time.sleep(0.5)

            except pyautogui.FailSafeException:
                self._set_status("⚠️ Fail-safe triggered", ModernStyle.COLORS['warning'])
                time.sleep(2)
            except Exception as e:
                self._set_status(f"❌ Error: {str(e)[:40]}", ModernStyle.COLORS['danger'])
                time.sleep(1)

        self.lol_window = None

    def search_accept_button(self, frame):
        """Search for accept button using template matching"""
        if self.template_gray is None:
            return None

        try:
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            result = cv2.matchTemplate(frame_gray, self.template_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= 0.8:
                th, tw = self.template_size
                center_x = max_loc[0] + tw // 2
                center_y = max_loc[1] + th // 2
                return (center_x, center_y)
            return None
        except Exception:
            return None


def main():
    root = tk.Tk()
    app = LoLAutoAcceptApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()