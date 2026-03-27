"""
CodingMacro - Desktop Macro Application
Independently schedules two parallel tasks:
  Task A: Press '1' at a configurable interval
  Task B: Type custom text + Enter at a configurable interval
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import keyboard


class CodingMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CodingMacro")
        self.root.resizable(False, False)

        # Shared state
        self.running = False
        self.countdown_active = False
        self.keystroke_lock = threading.Lock()  # Mutex for anti-collision
        self.stop_event = threading.Event()
        self.threads = []
        self.task_a_count = 0
        self.task_b_count = 0

        # Track all input widgets so we can disable/enable them
        self._input_widgets = []

        # --- Task A Section ---
        frame_a = ttk.LabelFrame(root, text="Task A - Repeatedly Press '1'", padding=10)
        frame_a.pack(padx=10, pady=(10, 5), fill="x")

        self.task_a_enabled = tk.BooleanVar(value=True)
        cb_a = ttk.Checkbutton(frame_a, text="Enable Task A", variable=self.task_a_enabled)
        cb_a.pack(anchor="w")
        self._input_widgets.append(cb_a)

        interval_a_frame = ttk.Frame(frame_a)
        interval_a_frame.pack(anchor="w", pady=(5, 0))
        ttk.Label(interval_a_frame, text="Interval:").pack(side="left")
        self.task_a_interval = tk.StringVar(value="3")
        entry_a = ttk.Entry(interval_a_frame, textvariable=self.task_a_interval, width=6)
        entry_a.pack(side="left", padx=5)
        self._input_widgets.append(entry_a)
        ttk.Label(interval_a_frame, text="seconds").pack(side="left")

        # --- Task B Section ---
        frame_b = ttk.LabelFrame(root, text="Task B - Custom Text + Enter", padding=10)
        frame_b.pack(padx=10, pady=5, fill="x")

        self.task_b_enabled = tk.BooleanVar(value=True)
        cb_b = ttk.Checkbutton(frame_b, text="Enable Task B", variable=self.task_b_enabled)
        cb_b.pack(anchor="w")
        self._input_widgets.append(cb_b)

        text_frame = ttk.Frame(frame_b)
        text_frame.pack(anchor="w", fill="x", pady=(5, 0))
        ttk.Label(text_frame, text="Text:").pack(side="left")
        self.task_b_text = tk.StringVar(value="go on process to make it better")
        entry_b_text = ttk.Entry(text_frame, textvariable=self.task_b_text, width=40)
        entry_b_text.pack(side="left", padx=5, fill="x", expand=True)
        self._input_widgets.append(entry_b_text)

        interval_b_frame = ttk.Frame(frame_b)
        interval_b_frame.pack(anchor="w", pady=(5, 0))
        ttk.Label(interval_b_frame, text="Interval:").pack(side="left")
        self.task_b_interval = tk.StringVar(value="10")
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

        # Always-on-top toggle
        self.on_top_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            controls_frame, text="Always on top", variable=self.on_top_var,
            command=self._toggle_on_top,
        ).pack(pady=(8, 0))

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

        # Lock UI inputs
        self._set_inputs_state("disabled")
        self.play_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_event.clear()
        self.task_a_count = 0
        self.task_b_count = 0
        self.countdown_active = True

        # Start countdown in a thread so UI stays responsive
        threading.Thread(
            target=self._countdown_then_start,
            args=(a_enabled, b_enabled, interval_a, interval_b),
            daemon=True,
        ).start()

    def on_stop(self):
        self._stop_tasks()

    def _emergency_stop(self):
        # Can be called from any thread via keyboard hook
        self.root.after(0, self._stop_tasks)

    def _stop_tasks(self):
        if not self.running and not self.countdown_active:
            return
        self.stop_event.set()
        self.running = False
        self.countdown_active = False
        # Wait briefly for threads to finish
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
        # Schedule next update
        self.root.after(500, self._update_live_status, a_enabled, b_enabled, interval_a, interval_b)

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

        # Start live status updates on the main thread
        self.root.after(0, self._update_live_status, a_enabled, b_enabled, interval_a, interval_b)

        # Launch task threads
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
        while not self.stop_event.is_set():
            with self.keystroke_lock:
                if self.stop_event.is_set():
                    break
                keyboard.write("1")
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
        self._stop_tasks()
        keyboard.unhook_all()
        self.root.destroy()


def main():
    root = tk.Tk()
    CodingMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
