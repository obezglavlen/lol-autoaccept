"""Image-driven auto-clicker with a quiet, Apple-inspired interface."""

import ctypes
from ctypes import wintypes
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
import time
import threading
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageOps
import psutil
from tkinterdnd2 import DND_FILES, TkinterDnD

from image_storage import (
    default_template_path,
    first_supported_drop_path,
    persist_template,
)
from process_selection import (
    collect_window_processes,
    default_process_path,
    load_process_selection,
    persist_process_selection,
)


class ModernStyle:
    """Apple-inspired light palette and typography."""
    COLORS = {
        'primary': '#0071e3',
        'primary_hover': '#0077ed',
        'primary_pressed': '#0068d1',
        'secondary': '#1d1d1f',
        'accent': '#0071e3',
        'bg_app': '#f5f5f7',
        'bg_dark': '#f5f5f7',
        'bg_card': '#ffffff',
        'bg_subtle': '#f5f5f7',
        'bg_hover': '#e8e8ed',
        'separator': '#d2d2d7',
        'text_main': '#1d1d1f',
        'text_dim': '#6e6e73',
        'text_quiet': '#86868b',
        'danger': '#ff3b30',
        'warning': '#ff9f0a',
        'success': '#34c759',
        'disabled': '#d1d1d6',
    }

    @staticmethod
    def style_tk(root):
        """Apply the restrained system typography used by the interface."""
        root.configure(bg=ModernStyle.COLORS['bg_app'])
        root.option_add('*Font', ('Segoe UI', 10))


def render_rounded_rectangle_image(
    width,
    height,
    radius,
    fill,
    *,
    outline=None,
    outline_width=0,
    supersample=4,
):
    """Render an anti-aliased rounded rectangle using supersampling."""
    if width <= 0 or height <= 0:
        raise ValueError("Rounded surface dimensions must be positive")

    scale = max(2, int(supersample))
    image = Image.new('RGBA', (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    inset = scale
    draw.rounded_rectangle(
        (inset, inset, width * scale - inset - 1, height * scale - inset - 1),
        radius=max(0, int(radius * scale)),
        fill=fill,
        outline=outline,
        width=max(1, int(outline_width * scale)) if outline else 1,
    )
    return image.resize((width, height), Image.Resampling.LANCZOS)


def create_rounded_surface(
    canvas,
    width,
    height,
    radius,
    fill,
    *,
    x=0,
    y=0,
    outline=None,
    outline_width=0,
    tags=(),
):
    """Place an anti-aliased rounded PIL surface on a Tk canvas."""
    image = render_rounded_rectangle_image(
        width,
        height,
        radius,
        fill,
        outline=outline,
        outline_width=outline_width,
    )
    photo = ImageTk.PhotoImage(image, master=canvas)
    item = canvas.create_image(x, y, anchor='nw', image=photo, tags=tags)
    return item, photo


class AppleButton(tk.Canvas):
    """A compact pill button with Apple-like interaction states."""

    def __init__(
        self,
        parent,
        *,
        text,
        command,
        width,
        height=46,
        fill=None,
        hover_fill=None,
        pressed_fill=None,
        text_color='#ffffff',
        disabled_fill=None,
        disabled_text='#86868b',
        font=('Segoe UI', 10, 'bold'),
    ):
        self.fill = fill or ModernStyle.COLORS['primary']
        self.hover_fill = hover_fill or ModernStyle.COLORS['primary_hover']
        self.pressed_fill = pressed_fill or ModernStyle.COLORS['primary_pressed']
        self.disabled_fill = disabled_fill or ModernStyle.COLORS['disabled']
        self.text_color = text_color
        self.disabled_text = disabled_text
        self.button_text = text
        self.command = command
        self.button_width = width
        self.button_height = height
        self.radius = height // 2
        self.enabled = True
        self.current_fill = self.fill
        self._font = font

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget('bg'),
            highlightthickness=0,
            bd=0,
            cursor='hand2',
            takefocus=1,
        )
        self._draw()
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<space>', lambda _event: self.invoke())
        self.bind('<Return>', lambda _event: self.invoke())

    def _draw(self):
        self.delete('all')
        surface = render_rounded_rectangle_image(
            self.button_width,
            self.button_height,
            self.radius,
            self.current_fill,
        )
        self.surface_photo = ImageTk.PhotoImage(surface, master=self)
        self.create_image(
            self.button_width // 2,
            self.button_height // 2,
            image=self.surface_photo,
            tags=('button_surface',),
        )
        self.create_text(
            self.button_width // 2,
            self.button_height // 2,
            text=self.button_text,
            fill=self.text_color if self.enabled else self.disabled_text,
            font=self._font,
        )

    def _on_enter(self, _event):
        if self.enabled:
            self.current_fill = self.hover_fill
            self._draw()

    def _on_leave(self, _event):
        if self.enabled:
            self.current_fill = self.fill
            self._draw()

    def _on_press(self, _event):
        if self.enabled:
            self.current_fill = self.pressed_fill
            self._draw()

    def _on_release(self, event):
        if not self.enabled:
            return
        inside = 0 <= event.x <= self.button_width and 0 <= event.y <= self.button_height
        self.current_fill = self.hover_fill if inside else self.fill
        self._draw()
        if inside and self.command:
            self.command()

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.current_fill = self.fill if self.enabled else self.disabled_fill
        self.configure(cursor='hand2' if self.enabled else 'arrow')
        self._draw()

    def set_text(self, text):
        self.button_text = text
        self._draw()

    def invoke(self):
        if self.enabled and self.command:
            self.command()


class AppleDropdown(tk.Canvas):
    """Rounded process selector backed by a native popup menu."""

    def __init__(
        self,
        parent,
        *,
        textvariable,
        width,
        height=36,
        values=(),
        command=None,
    ):
        self.dropdown_width = width
        self.dropdown_height = height
        self.radius = 12
        self.variable = textvariable
        self.values = tuple(values)
        self.command = command
        self.current_fill = ModernStyle.COLORS['bg_subtle']
        self.surface_photo = None

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget('bg'),
            highlightthickness=0,
            bd=0,
            cursor='hand2',
            takefocus=1,
        )
        self._variable_trace = self.variable.trace_add('write', self._on_text_changed)
        self._draw()
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._open_menu)
        self.bind('<Return>', self._open_menu)
        self.bind('<space>', self._open_menu)

    def _draw(self):
        self.delete('all')
        surface = render_rounded_rectangle_image(
            self.dropdown_width,
            self.dropdown_height,
            self.radius,
            self.current_fill,
            outline=ModernStyle.COLORS['separator'],
            outline_width=1,
        )
        self.surface_photo = ImageTk.PhotoImage(surface, master=self)
        self.create_image(
            self.dropdown_width // 2,
            self.dropdown_height // 2,
            image=self.surface_photo,
            tags=('dropdown_surface',),
        )
        label = self.variable.get()
        if len(label) > 42:
            label = f"{label[:39]}…"
        self.create_text(
            14,
            self.dropdown_height // 2,
            anchor='w',
            text=label,
            fill=ModernStyle.COLORS['text_main'],
            font=('Segoe UI', 9),
        )
        self.create_text(
            self.dropdown_width - 17,
            self.dropdown_height // 2 - 1,
            text='▾',
            fill=ModernStyle.COLORS['text_dim'],
            font=('Segoe UI', 10),
        )

    def _on_text_changed(self, *_args):
        self._draw()

    def _on_enter(self, _event):
        self.current_fill = ModernStyle.COLORS['bg_hover']
        self._draw()

    def _on_leave(self, _event):
        self.current_fill = ModernStyle.COLORS['bg_subtle']
        self._draw()

    def _open_menu(self, _event=None):
        menu = tk.Menu(
            self,
            tearoff=False,
            font=('Segoe UI', 9),
            bg=ModernStyle.COLORS['bg_card'],
            fg=ModernStyle.COLORS['text_main'],
            activebackground=ModernStyle.COLORS['primary'],
            activeforeground='#ffffff',
        )
        if self.values:
            for index, label in enumerate(self.values):
                menu.add_command(
                    label=label,
                    command=lambda item=index: self._choose(item),
                )
        else:
            menu.add_command(label='No windowed processes found', state='disabled')

        try:
            menu.tk_popup(
                self.winfo_rootx(),
                self.winfo_rooty() + self.dropdown_height,
            )
        finally:
            menu.grab_release()

    def _choose(self, index):
        self.current(index)
        if self.command:
            self.command()
        else:
            self.event_generate('<<ComboboxSelected>>', when='tail')

    def set_values(self, values):
        self.values = tuple(values)
        current_index = self.current()
        if current_index is not None and current_index >= len(self.values):
            self.variable.set('Choose a process…')
        self._draw()

    def current(self, index=None):
        if index is None:
            try:
                return self.values.index(self.variable.get())
            except ValueError:
                return -1

        index = int(index)
        if index < 0 or index >= len(self.values):
            raise tk.TclError('process selection index out of range')
        self.variable.set(self.values[index])

    def cget(self, key):
        if key == 'values':
            return self.values
        return super().cget(key)

    def destroy(self):
        try:
            self.variable.trace_remove('write', self._variable_trace)
        except tk.TclError:
            pass
        super().destroy()


class LoLAutoAcceptApp:
    def __init__(
        self,
        root,
        template_path=None,
        process_path=None,
        process_provider=None,
    ):
        self.root = root
        self.root.title("Auto Accept")
        self.root.geometry("520x770")
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
        self.target_window = None
        self._target_rect = None
        self.template_path = Path(template_path) if template_path else default_template_path()
        self.process_path = (
            Path(process_path) if process_path else default_process_path()
        )
        self.process_provider = process_provider or self._list_window_processes
        self.process_targets = []
        self.selected_process = load_process_selection(self.process_path)
        
        self._set_window_icon()
        
        self.setup_ui()
        self._refresh_processes()
        self._setup_drag_and_drop()
        self._restore_saved_template()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _set_window_icon(self):
        """Create a crisp in-memory icon so source and EXE match."""
        image = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (1, 1, 30, 30),
            radius=8,
            fill=ModernStyle.COLORS['primary'],
        )
        try:
            font = ImageFont.truetype('segoeuib.ttf', 19)
        except OSError:
            font = ImageFont.load_default()
        bounds = draw.textbbox((0, 0), 'A', font=font)
        text_width = bounds[2] - bounds[0]
        text_height = bounds[3] - bounds[1]
        draw.text(
            ((32 - text_width) / 2, (32 - text_height) / 2 - bounds[1]),
            'A',
            fill='#ffffff',
            font=font,
        )
        self.app_icon = ImageTk.PhotoImage(image, master=self.root)
        self.root.iconphoto(True, self.app_icon)

    def setup_ui(self):
        """Create an airy Apple-inspired interface."""
        colors = ModernStyle.COLORS

        header = tk.Frame(self.root, bg=colors['bg_app'])
        header.pack(fill='x', padx=28, pady=(28, 18))

        icon = tk.Canvas(
            header,
            width=50,
            height=50,
            bg=colors['bg_app'],
            highlightthickness=0,
        )
        icon.pack(side='left')
        _, self.header_icon_photo = create_rounded_surface(
            icon,
            50,
            50,
            14,
            colors['primary'],
        )
        icon.create_text(
            25,
            25,
            text='A',
            fill='#ffffff',
            font=('Segoe UI', 18, 'bold'),
        )

        title_stack = tk.Frame(header, bg=colors['bg_app'])
        title_stack.pack(side='left', padx=(14, 0), anchor='center')
        self.title_label = tk.Label(
            title_stack,
            text='Auto Accept',
            font=('Segoe UI', 25, 'bold'),
            fg=colors['text_main'],
            bg=colors['bg_app'],
            anchor='w',
        )
        self.title_label.pack(anchor='w')
        tk.Label(
            title_stack,
            text='A quieter way to catch every match.',
            font=('Segoe UI', 10),
            fg=colors['text_dim'],
            bg=colors['bg_app'],
            anchor='w',
        ).pack(anchor='w', pady=(2, 0))

        self.card_canvas = tk.Canvas(
            self.root,
            width=472,
            height=578,
            bg=colors['bg_app'],
            highlightthickness=0,
        )
        self.card_canvas.pack()
        _, self.card_shadow_photo = create_rounded_surface(
            self.card_canvas,
            464,
            567,
            22,
            '#e3e3e8',
            x=4,
            y=7,
            tags=('card_shadow',),
        )
        _, self.card_surface_photo = create_rounded_surface(
            self.card_canvas,
            466,
            567,
            22,
            colors['bg_card'],
            x=1,
            y=1,
            tags=('card_surface',),
        )

        card = tk.Frame(
            self.card_canvas,
            bg=colors['bg_card'],
            width=424,
            height=524,
        )
        card.pack_propagate(False)
        self.card_canvas.create_window(
            22,
            22,
            anchor='nw',
            window=card,
            width=424,
            height=524,
        )

        section_header = tk.Frame(card, bg=colors['bg_card'])
        section_header.pack(fill='x')
        tk.Label(
            section_header,
            text='ACCEPT BUTTON',
            font=('Segoe UI', 8, 'bold'),
            fg=colors['text_quiet'],
            bg=colors['bg_card'],
        ).pack(side='left')
        tk.Label(
            section_header,
            text='Saved automatically',
            font=('Segoe UI', 8),
            fg=colors['text_quiet'],
            bg=colors['bg_card'],
        ).pack(side='right')

        self.image_frame = tk.Frame(card, bg=colors['bg_card'])
        self.image_frame.pack(fill='x', pady=(10, 0))

        self.image_canvas = tk.Canvas(
            self.image_frame,
            width=424,
            height=142,
            bg=colors['bg_card'],
            highlightthickness=0,
            cursor='hand2',
        )
        self.image_canvas.pack(fill='x')
        self.drop_border, self.drop_surface_photo = create_rounded_surface(
            self.image_canvas,
            424,
            142,
            14,
            colors['bg_subtle'],
            outline=colors['separator'],
            outline_width=1,
            tags=('drop_border',),
        )
        self.drop_icon = self.image_canvas.create_text(
            212,
            37,
            text='+',
            fill=colors['primary'],
            font=('Segoe UI', 22),
            tags=('drop_placeholder',),
        )
        self.image_placeholder = self.image_canvas.create_text(
            212,
            69,
            text='Drop image here',
            fill=colors['text_main'],
            font=('Segoe UI', 11, 'bold'),
            tags=('drop_placeholder',),
        )
        self.drop_hint = self.image_canvas.create_text(
            212,
            96,
            text='PNG, JPG, JPEG or BMP',
            fill=colors['text_quiet'],
            font=('Segoe UI', 9),
            tags=('drop_placeholder',),
        )
        self.image_canvas.bind('<Configure>', self._on_canvas_configure)
        self.image_canvas.bind('<Button-1>', lambda _event: self.browse_image())

        self.browse_btn = AppleButton(
            card,
            text='Choose image',
            command=self.browse_image,
            width=156,
            height=38,
            fill=colors['bg_hover'],
            hover_fill='#dedee3',
            pressed_fill='#c7c7cc',
            text_color=colors['text_main'],
            font=('Segoe UI', 9, 'bold'),
        )
        self.browse_btn.pack(pady=(12, 16))

        tk.Frame(card, bg=colors['separator'], height=1).pack(fill='x')

        process_header = tk.Frame(card, bg=colors['bg_card'])
        process_header.pack(fill='x', pady=(14, 8))
        tk.Label(
            process_header,
            text='PROCESS WINDOW',
            font=('Segoe UI', 8, 'bold'),
            fg=colors['text_quiet'],
            bg=colors['bg_card'],
        ).pack(side='left')
        tk.Label(
            process_header,
            text='Saved automatically',
            font=('Segoe UI', 8),
            fg=colors['text_quiet'],
            bg=colors['bg_card'],
        ).pack(side='right')

        process_row = tk.Frame(card, bg=colors['bg_card'])
        process_row.pack(fill='x', pady=(0, 16))
        self.process_var = tk.StringVar(value='Choose a process…')
        self.process_combo = AppleDropdown(
            process_row,
            textvariable=self.process_var,
            width=334,
            height=36,
            command=self._on_process_selected,
        )
        self.process_combo.pack(side='left')

        self.refresh_process_btn = AppleButton(
            process_row,
            text='Refresh',
            command=self._refresh_processes,
            width=82,
            height=36,
            fill=colors['bg_hover'],
            hover_fill='#dedee3',
            pressed_fill='#c7c7cc',
            text_color=colors['text_main'],
            font=('Segoe UI', 8, 'bold'),
        )
        self.refresh_process_btn.pack(side='right', padx=(8, 0))

        tk.Frame(card, bg=colors['separator'], height=1).pack(fill='x')

        tk.Label(
            card,
            text='STATUS',
            font=('Segoe UI', 8, 'bold'),
            fg=colors['text_quiet'],
            bg=colors['bg_card'],
        ).pack(anchor='w', pady=(14, 8))

        self.status_canvas = tk.Canvas(
            card,
            width=424,
            height=54,
            bg=colors['bg_card'],
            highlightthickness=0,
        )
        self.status_canvas.pack(fill='x')
        _, self.status_surface_photo = create_rounded_surface(
            self.status_canvas,
            424,
            54,
            14,
            colors['bg_subtle'],
        )
        status_dot_image = render_rounded_rectangle_image(
            10,
            10,
            5,
            colors['text_quiet'],
        )
        self.status_dot_photo = ImageTk.PhotoImage(
            status_dot_image,
            master=self.status_canvas,
        )
        self.status_dot = self.status_canvas.create_image(
            22,
            27,
            image=self.status_dot_photo,
        )
        self.status_label = tk.Label(
            self.status_canvas,
            text='Ready to start',
            font=('Segoe UI', 10),
            fg=colors['text_main'],
            bg=colors['bg_subtle'],
        )
        self.status_canvas.create_window(
            38,
            27,
            anchor='w',
            window=self.status_label,
        )

        controls = tk.Frame(card, bg=colors['bg_card'])
        controls.pack(fill='x', pady=(18, 0))
        self.start_btn = AppleButton(
            controls,
            text='Start scanning',
            command=self.start_app,
            width=202,
            height=46,
            fill=colors['primary'],
            hover_fill=colors['primary_hover'],
            pressed_fill=colors['primary_pressed'],
        )
        self.start_btn.pack(side='left')

        self.stop_btn = AppleButton(
            controls,
            text='Stop',
            command=self.stop_app,
            width=202,
            height=46,
            fill=colors['bg_hover'],
            hover_fill='#dedee3',
            pressed_fill='#c7c7cc',
            text_color=colors['text_main'],
        )
        self.stop_btn.pack(side='right')
        self.stop_btn.set_enabled(False)

        footer = tk.Frame(self.root, bg=colors['bg_app'])
        footer.pack(fill='x', pady=(15, 0))
        tk.Label(
            footer,
            text='Runs locally  ·  Scans only the selected process window',
            font=('Segoe UI', 9),
            fg=colors['text_quiet'],
            bg=colors['bg_app'],
        ).pack()

    def _list_window_processes(self):
        """Return selectable process targets that currently own a window."""
        return collect_window_processes(
            pyautogui.getAllWindows(),
            pid_resolver=self._window_process_id,
            name_resolver=lambda pid: psutil.Process(pid).name(),
            excluded_pids=(os.getpid(),),
        )

    @staticmethod
    def _window_process_id(window):
        """Resolve a PyGetWindow handle to its owning Windows process ID."""
        process_id = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(
            wintypes.HWND(window._hWnd),
            ctypes.byref(process_id),
        )
        return process_id.value

    def _refresh_processes(self):
        """Reload the process selector while preserving a saved choice."""
        try:
            targets = list(self.process_provider())
        except Exception:
            targets = []

        self.process_targets = targets
        labels = tuple(target.label for target in targets)
        self.process_combo.set_values(labels)

        selected = self.selected_process
        match = None
        if selected:
            match = next(
                (
                    target
                    for target in targets
                    if target.pid == selected.pid and target.name == selected.name
                ),
                None,
            )
            if match is None:
                match = next(
                    (
                        target
                        for target in targets
                        if target.name.casefold() == selected.name.casefold()
                    ),
                    None,
                )

        if match:
            self.selected_process = match
            self.process_var.set(match.label)
        elif selected:
            self.process_var.set(f"{selected.name}  (not running)")
        else:
            self.process_var.set('Choose a process…')

    def _on_process_selected(self, _event=None):
        """Handle a process choice from the read-only selector."""
        index = self.process_combo.current()
        if index is None or index < 0 or index >= len(self.process_targets):
            return

        target = self.process_targets[index]
        try:
            persist_process_selection(target, self.process_path)
        except OSError:
            self._set_status(
                "Process selection could not be saved",
                ModernStyle.COLORS['danger'],
            )
            return

        self.selected_process = target
        self.process_var.set(target.label)
        self._set_status(
            f"Selected: {target.name}",
            ModernStyle.COLORS['success'],
        )

    def browse_image(self):
        """Open file dialog to select template image."""
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.bmp"),
            ("All files", "*.*")
        ]
        file_path = filedialog.askopenfilename(
            title="Select accept button image",
            filetypes=filetypes
        )

        if file_path:
            self._load_template_image(file_path, persist=True)

    def _setup_drag_and_drop(self):
        """Register the preview area as a native file drop target."""
        for widget in (self.image_frame, self.image_canvas):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_image_drop)

    def _on_image_drop(self, event):
        """Load the first supported image from a native file drop."""
        dropped_path = first_supported_drop_path(event.data, self.root.tk.splitlist)
        if dropped_path is None:
            self._set_status(
                "Choose a PNG, JPG, JPEG, or BMP image",
                ModernStyle.COLORS['danger'],
            )
            return getattr(event, "action", "copy")

        self._load_template_image(dropped_path, persist=True)
        return getattr(event, "action", "copy")

    def _restore_saved_template(self):
        """Restore the persisted template when the application starts."""
        if not self.template_path.is_file():
            return

        loaded = self._load_template_image(
            self.template_path,
            persist=False,
            notify_error=False,
            success_message="Saved template restored",
        )
        if not loaded:
            self.template_path.unlink(missing_ok=True)

    def _load_template_image(
        self,
        file_path,
        *,
        persist,
        notify_error=True,
        success_message="Template loaded and saved",
    ):
        """Validate, display, and optionally persist a template image."""
        try:
            selected_path = Path(file_path)
            active_path = (
                persist_template(selected_path, self.template_path)
                if persist
                else selected_path
            )
            self._render_template_preview(active_path)
            self.image_path = str(active_path)
            self._set_status(success_message, ModernStyle.COLORS['success'])
            return True
        except Exception as e:
            self.image_path = None
            if notify_error:
                messagebox.showerror("Error", f"Failed to load image: {e}")
            self._set_status("Image could not be loaded", ModernStyle.COLORS['danger'])
            return False

    def _render_template_preview(self, image_path):
        """Render a centered preview in the image canvas."""
        with Image.open(image_path) as opened:
            img = ImageOps.exif_transpose(opened).convert("RGB")
            self.image_canvas.update_idletasks()
            canvas_width = max(
                self.image_canvas.winfo_width(),
                self.image_canvas.winfo_reqwidth(),
                1,
            )
            canvas_height = max(
                self.image_canvas.winfo_height(),
                self.image_canvas.winfo_reqheight(),
                1,
            )

            img_width, img_height = img.size
            if img_width <= 0 or img_height <= 0:
                raise ValueError("Image has invalid dimensions")

            available_width = max(1, canvas_width - 16)
            available_height = max(1, canvas_height - 16)
            scale = min(available_width / img_width, available_height / img_height, 1.0)
            new_width = max(1, int(img_width * scale))
            new_height = max(1, int(img_height * scale))
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(resized_img)

        self.image_canvas.delete("template_preview")
        self.image_canvas.itemconfigure("drop_placeholder", state="hidden")
        self.image_canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor='center',
            image=photo,
            tags=("template_preview",),
        )
        self.image_canvas.tag_lower("drop_border")
        self.image_canvas.image = photo

    def _on_canvas_configure(self, event):
        """Keep drop-zone elements aligned whenever the canvas resizes."""
        center_x = event.width // 2
        center_y = event.height // 2
        self.image_canvas.coords("drop_border", 0, 0)
        if self.image_placeholder:
            self.image_canvas.coords(self.drop_icon, center_x, center_y - 34)
            self.image_canvas.coords(self.image_placeholder, center_x, center_y)
            self.image_canvas.coords(self.drop_hint, center_x, center_y + 27)
        self.image_canvas.coords(
            "template_preview",
            center_x,
            center_y,
        )
    
    def _center_placeholder(self):
        """Recenter placeholder (convenience for external callers)"""
        if self.image_placeholder:
            w = self.image_canvas.winfo_width()
            h = self.image_canvas.winfo_height()
            self.image_canvas.coords(self.drop_icon, w // 2, h // 2 - 34)
            self.image_canvas.coords(self.image_placeholder, w // 2, h // 2)
            self.image_canvas.coords(self.drop_hint, w // 2, h // 2 + 27)
    
    def _set_status(self, text, color=None):
        """Update the status copy and its compact color indicator."""
        if color:
            dot_image = render_rounded_rectangle_image(10, 10, 5, color)
            self.status_dot_photo = ImageTk.PhotoImage(
                dot_image,
                master=self.status_canvas,
            )
            self.status_canvas.itemconfigure(
                self.status_dot,
                image=self.status_dot_photo,
            )
        self.status_label.config(text=text, fg=ModernStyle.COLORS['text_main'])

    def _set_buttons(self, running):
        """Toggle button states"""
        self.start_btn.set_enabled(not running)
        self.stop_btn.set_enabled(running)
        self.start_btn.set_text("Scanning…" if running else "Start scanning")

    def _find_selected_window(self):
        """Find the largest visible window owned by the selected process."""
        if self.selected_process is None:
            return None

        matches = []
        for window in pyautogui.getAllWindows():
            try:
                if (
                    self._window_process_id(window) == self.selected_process.pid
                    and getattr(window, 'visible', True)
                    and not getattr(window, 'isMinimized', False)
                    and window.width > 0
                    and window.height > 0
                ):
                    matches.append(window)
            except Exception:
                continue

        if not matches:
            return None
        return max(matches, key=lambda window: window.width * window.height)

    def start_app(self):
        """Start monitoring"""
        if not self.image_path:
            messagebox.showwarning("Warning", "Upload accept button image first!")
            return

        if self.selected_process is None:
            messagebox.showwarning("Warning", "Choose a process to scan first!")
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

        self._refresh_processes()
        self.target_window = self._find_selected_window()
        if not self.target_window:
            process_name = self.selected_process.name
            self._set_status(
                f"Window for {process_name} was not found",
                ModernStyle.COLORS['danger'],
            )
            messagebox.showerror(
                "Error",
                f"A visible window for {process_name} was not found.",
            )
            return

        try:
            self.target_window.activate()
            time.sleep(0.2)
        except Exception:
            self._set_status(
                "Could not activate the selected window",
                ModernStyle.COLORS['warning'],
            )
            return

        try:
            self._target_rect = (
                self.target_window.left,
                self.target_window.top,
                self.target_window.width,
                self.target_window.height,
            )
        except Exception:
            self._target_rect = None

        self.is_running = True
        self._stop_event.clear()
        self._set_status(
            f"Scanning {self.selected_process.name}…",
            ModernStyle.COLORS['primary'],
        )
        self._set_buttons(True)

        self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()

    def stop_app(self):
        """Stop monitoring"""
        self.is_running = False
        self._stop_event.set()
        self.target_window = None
        self._set_status("Scanning stopped", ModernStyle.COLORS['text_quiet'])
        self._set_buttons(False)

    def on_close(self):
        """Handle window close"""
        if self.is_running:
            self.stop_app()
        self.root.destroy()

    def _capture_target_frame(self):
        """Capture only the current bounds of the selected process window."""
        if self.target_window is None:
            raise RuntimeError("Selected process window is unavailable")

        rect = (
            int(self.target_window.left),
            int(self.target_window.top),
            int(self.target_window.width),
            int(self.target_window.height),
        )
        if rect[2] <= 0 or rect[3] <= 0:
            raise RuntimeError("Selected process window has invalid bounds")

        self._target_rect = rect
        screenshot = pyautogui.screenshot(region=rect)
        return np.array(screenshot), rect

    def _is_selected_process_running(self):
        """Check that the saved PID still belongs to the selected executable."""
        if self.selected_process is None:
            return False
        try:
            process = psutil.Process(self.selected_process.pid)
            return (
                process.is_running()
                and process.name().casefold() == self.selected_process.name.casefold()
            )
        except psutil.Error:
            return False

    def _run_monitor(self):
        """Background monitoring thread"""
        while self.is_running and not self._stop_event.is_set():
            try:
                if not self._is_selected_process_running():
                    self._set_status(
                        "Selected process is not running — paused",
                        ModernStyle.COLORS['warning'],
                    )
                    self._stop_event.wait(1)
                    continue

                if (
                    not self.target_window
                    or not getattr(self.target_window, 'visible', True)
                    or getattr(self.target_window, 'isMinimized', False)
                ):
                    self.target_window = self._find_selected_window()
                    if not self.target_window:
                        self._set_status(
                            "Selected process window was lost",
                            ModernStyle.COLORS['warning'],
                        )
                        self._stop_event.wait(1)
                        continue

                frame, rect = self._capture_target_frame()

                accept_pos = self.search_accept_button(frame)

                if accept_pos:
                    click_x = rect[0] + accept_pos[0]
                    click_y = rect[1] + accept_pos[1]
                    self._set_status("Target found — clicking", ModernStyle.COLORS['success'])
                    pyautogui.click(click_x, click_y)
                    self._stop_event.wait(3)
                else:
                    self._set_status(
                        f"Scanning {self.selected_process.name}…",
                        ModernStyle.COLORS['primary'],
                    )
                    self._stop_event.wait(0.5)

            except pyautogui.FailSafeException:
                self._set_status("Safety stop triggered", ModernStyle.COLORS['warning'])
                self._stop_event.wait(2)
            except Exception as e:
                self._set_status(f"Error: {str(e)[:40]}", ModernStyle.COLORS['danger'])
                self._stop_event.wait(1)

        self.target_window = None

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
    root = TkinterDnD.Tk()
    app = LoLAutoAcceptApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()