"""
CodingMacro - Desktop Macro Application
Independently schedules two parallel tasks:
  Task A: Press a configurable key at a configurable interval
  Task B: Type custom text + Enter at a configurable interval
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import json
import os
import sys
import keyboard


SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")

DEFAULT_SETTINGS = {
    "task_a_enabled": True,
    "task_a_key": "1",
    "task_a_interval": "3",
    "task_b_enabled": True,
    "task_b_text": "go on process to make it better",
    "task_b_interval": "10",
    "always_on_top": False,
}


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # Merge with defaults so new keys are always present
        merged = {**DEFAULT_SETTINGS, **saved}
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)


def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class CodingMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CodingMacro")
        self.root.resizable(False, False)

        # Load saved settings
        settings = load_settings()

        # Shared state
        self.running = False
        self.countdown_active = False
        self.keystroke_lock = threading.Lock()  # Mutex for anti-collision
        self.stop_event = threading.Event()
        self.threads = []
        self.task_a_count = 0
        self.task_b_count = 0
        self._tray_icon = None

        # Track all input widgets so we can disable/enable them
        self._input_widgets = []

        # --- Task A Section ---
        frame_a = ttk.LabelFrame(root, text="Task A - Repeatedly Press Key", padding=10)
        frame_a.pack(padx=10, pady=(10, 5), fill="x")

        self.task_a_enabled = tk.BooleanVar(value=settings["task_a_enabled"])
        cb_a = ttk.Checkbutton(frame_a, text="Enable Task A", variable=self.task_a_enabled)
        cb_a.pack(anchor="w")
        self._input_widgets.append(cb_a)

        key_frame = ttk.Frame(frame_a)
        key_frame.pack(anchor="w", pady=(5, 0))
        ttk.Label(key_frame, text="Key:").pack(side="left")
        self.task_a_key = tk.StringVar(value=settings["task_a_key"])
        entry_a_key = ttk.Entry(key_frame, textvariable=self.task_a_key, width=8)
        entry_a_key.pack(side="left", padx=5)
        self._input_widgets.append(entry_a_key)

        interval_a_frame = ttk.Frame(frame_a)
        interval_a_frame.pack(anchor="w", pady=(5, 0))
        ttk.Label(interval_a_frame, text="Interval:").pack(side="left")
        self.task_a_interval = tk.StringVar(value=settings["task_a_interval"])
        entry_a = ttk.Entry(interval_a_frame, textvariable=self.task_a_interval, width=6)
        entry_a.pack(side="left", padx=5)
        self._input_widgets.append(entry_a)
        ttk.Label(interval_a_frame, text="seconds").pack(side="left")

        # --- Task B Section ---
        frame_b = ttk.LabelFrame(root, text="Task B - Custom Text + Enter", padding=10)
        frame_b.pack(padx=10, pady=5, fill="x")

        self.task_b_enabled = tk.BooleanVar(value=settings["task_b_enabled"])
        cb_b = ttk.Checkbutton(frame_b, text="Enable Task B", variable=self.task_b_enabled)
        cb_b.pack(anchor="w")
        self._input_widgets.append(cb_b)

        text_frame = ttk.Frame(frame_b)
        text_frame.pack(anchor="w", fill="x", pady=(5, 0))
        ttk.Label(text_frame, text="Text:").pack(side="left")
        self.task_b_text = tk.StringVar(value=settings["task_b_text"])
        entry_b_text = ttk.Entry(text_frame, textvariable=self.task_b_text, width=40)
        entry_b_text.pack(side="left", padx=5, fill="x", expand=True)
        self._input_widgets.append(entry_b_text)

        interval_b_frame = ttk.Frame(frame_b)
        interval_b_frame.pack(anchor="w", pady=(5, 0))
        ttk.Label(interval_b_frame, text="Interval:").pack(side="left")
        self.task_b_interval = tk.StringVar(value=settings["task_b_interval"])
        entry_b_int = ttk.Entry(interval_b_frame, textvariable=self.task_b_interval, width=6)
        entry_b_int.pack(side="left", padx=5)
        self._input_widgets.append(entry_b_int)
        ttk.Label(interval_b_frame, text="seconds").pack(side="left")

        # --- Global Controls ---
        controls_frame = ttk.LabelFrame(root, text="Global Controls", padding=10)
        controls_frame.pack(padx=10, pady=5, fill="x")

        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack()

        self.play_btn = ttk.Button(btn_frame, text="\u25b6 Play", command=self.on_play)
        self.play_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="\u23f9 Stop", command=self.on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        opts_frame = ttk.Frame(controls_frame)
        opts_frame.pack(pady=(8, 0))

        self.on_top_var = tk.BooleanVar(value=settings["always_on_top"])
        ttk.Checkbutton(
            opts_frame, text="Always on top", variable=self.on_top_var,
            command=self._toggle_on_top,
        ).pack(side="left", padx=8)

        ttk.Button(opts_frame, text="Minimize to tray", command=self._minimize_to_tray).pack(side="left", padx=8)

        # Apply saved always-on-top
        if settings["always_on_top"]:
            self.root.attributes("-topmost", True)

        # Color-coded status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(
            controls_frame, textvariable=self.status_var, relief="sunken",
            anchor="center", bg="#e0e0e0", font=("Segoe UI", 9),
        )
        self.status_bar.pack(fill="x", pady=(10, 0))

        # Hotkey hint
        ttk.Label(root, text="Emergency Stop: F12 / ESC", foreground="gray").pack(pady=(0, 10))

        # Register global emergency stop hotkeys
        keyboard.add_hotkey("F12", self._emergency_stop, suppress=False)
        keyboard.add_hotkey("escape", self._emergency_stop, suppress=False)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Controls ──────────────────────────────────────────────

    def on_play(self):
        if self.running or self.countdown_active:
            return

        a_enabled = self.task_a_enabled.get()
        b_enabled = self.task_b_enabled.get()

        if not a_enabled and not b_enabled:
            self._set_status("Enable at least one task!", "#e0e0e0")
            return

        # Validate intervals
        try:
            interval_a = float(self.task_a_interval.get()) if a_enabled else None
            interval_b = float(self.task_b_interval.get()) if b_enabled else None
            if (interval_a is not None and interval_a <= 0) or (interval_b is not None and interval_b <= 0):
                raise ValueError
        except ValueError:
            self._set_status("Invalid interval value!", "#e0e0e0")
            return

        # Save settings on play
        self._save_current_settings()

        # Lock UI inputs
        self._set_inputs_state("disabled")
        self.play_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_event.clear()
        self.task_a_count = 0
        self.task_b_count = 0
        self.countdown_active = True

        # Capture Task A key now (while UI is still accessible)
        self._task_a_key_value = self.task_a_key.get()

        # Start countdown in a thread so UI stays responsive
        threading.Thread(
            target=self._countdown_then_start,
            args=(a_enabled, b_enabled, interval_a, interval_b),
            daemon=True,
        ).start()

    def on_stop(self):
        self._stop_tasks()

    def _emergency_stop(self):
        self.root.after(0, self._stop_tasks)

    def _stop_tasks(self):
        if not self.running and not self.countdown_active:
            return
        self.stop_event.set()
        self.running = False
        self.countdown_active = False
        for t in self.threads:
            t.join(timeout=1)
        self.threads.clear()
        self._set_inputs_state("normal")
        self.play_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._set_status("Stopped", "#ffcccc")

    # ── UI Helpers ─────────────────────────────────────────────

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_bar.config(bg=color)

    def _set_inputs_state(self, state):
        for widget in self._input_widgets:
            widget.config(state=state)

    def _toggle_on_top(self):
        self.root.attributes("-topmost", self.on_top_var.get())

    def _update_live_status(self, a_enabled, b_enabled, interval_a, interval_b):
        if not self.running:
            return
        parts = []
        if a_enabled:
            parts.append(f"A: {self.task_a_count}x ({interval_a:.0f}s)")
        if b_enabled:
            parts.append(f"B: {self.task_b_count}x ({interval_b:.0f}s)")
        self._set_status(" | ".join(parts), "#ccffcc")
        self.root.after(500, self._update_live_status, a_enabled, b_enabled, interval_a, interval_b)

    # ── Settings ───────────────────────────────────────────────

    def _save_current_settings(self):
        data = {
            "task_a_enabled": self.task_a_enabled.get(),
            "task_a_key": self.task_a_key.get(),
            "task_a_interval": self.task_a_interval.get(),
            "task_b_enabled": self.task_b_enabled.get(),
            "task_b_text": self.task_b_text.get(),
            "task_b_interval": self.task_b_interval.get(),
            "always_on_top": self.on_top_var.get(),
        }
        save_settings(data)

    # ── System Tray ────────────────────────────────────────────

    def _minimize_to_tray(self):
        self.root.withdraw()
        try:
            import pystray
            from PIL import Image, ImageDraw

            # Create a simple icon
            img = Image.new("RGB", (64, 64), color=(50, 150, 50))
            draw = ImageDraw.Draw(img)
            draw.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
            draw.text((22, 20), "M", fill=(50, 150, 50))

            def on_restore(icon, item):
                icon.stop()
                self.root.after(0, self.root.deiconify)

            def on_quit(icon, item):
                icon.stop()
                self.root.after(0, self._on_close)

            menu = pystray.Menu(
                pystray.MenuItem("Restore", on_restore, default=True),
                pystray.MenuItem("Quit", on_quit),
            )
            self._tray_icon = pystray.Icon("CodingMacro", img, "CodingMacro", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()

        except ImportError:
            # pystray/Pillow not available — just minimize to taskbar instead
            self.root.iconify()
            self.root.deiconify()

    # ── Countdown ─────────────────────────────────────────────

    def _countdown_then_start(self, a_enabled, b_enabled, interval_a, interval_b):
        for remaining in range(5, 0, -1):
            if self.stop_event.is_set():
                self.countdown_active = False
                self.root.after(0, lambda: self._set_status("Stopped", "#ffcccc"))
                self.root.after(0, lambda: self._set_inputs_state("normal"))
                self.root.after(0, lambda: self.play_btn.config(state="normal"))
                self.root.after(0, lambda: self.stop_btn.config(state="disabled"))
                return
            self.root.after(0, lambda r=remaining: self._set_status(f"Starting in {r}...", "#ffffcc"))
            time.sleep(1)

        if self.stop_event.is_set():
            self.countdown_active = False
            return

        self.countdown_active = False
        self.running = True

        self.root.after(0, self._update_live_status, a_enabled, b_enabled, interval_a, interval_b)

        if a_enabled:
            t = threading.Thread(target=self._task_a_loop, args=(interval_a,), daemon=True)
            self.threads.append(t)
            t.start()

        if b_enabled:
            t = threading.Thread(target=self._task_b_loop, args=(interval_b,), daemon=True)
            self.threads.append(t)
            t.start()

    # ── Task Loops ────────────────────────────────────────────

    def _task_a_loop(self, interval):
        key = self._task_a_key_value
        while not self.stop_event.is_set():
            with self.keystroke_lock:
                if self.stop_event.is_set():
                    break
                keyboard.write(key)
                self.task_a_count += 1
            self._interruptible_sleep(interval)

    def _task_b_loop(self, interval):
        while not self.stop_event.is_set():
            text = self.task_b_text.get()
            with self.keystroke_lock:
                if self.stop_event.is_set():
                    break
                keyboard.write(text, delay=0.02)
                keyboard.press_and_release("enter")
                self.task_b_count += 1
            self._interruptible_sleep(interval)

    def _interruptible_sleep(self, duration):
        """Sleep in 0.1s chunks so we can respond to stop quickly."""
        end_time = time.monotonic() + duration
        while time.monotonic() < end_time:
            if self.stop_event.is_set():
                return
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.1, remaining))

    # ── Cleanup ───────────────────────────────────────────────

    def _on_close(self):
        self._save_current_settings()
        self._stop_tasks()
        if self._tray_icon:
            self._tray_icon.stop()
        keyboard.unhook_all()
        self.root.destroy()


def main():
    root = tk.Tk()
    CodingMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
