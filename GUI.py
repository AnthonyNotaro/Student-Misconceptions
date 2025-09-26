import tkinter as tk
from tkinter import ttk

PROBLEM_TEXT = (
    "Enter a 10-character answer (one character per box). "
    "Press Enter to submit."
)

# ----- App -----
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Grid Input Prompt")
        self.configure(bg="#0f1224")
        self._center_on_screen(760, 360)
        self._build_style()
        self._build_ui()

    # ----- UI -----
    def _build_ui(self):
        wrapper = ttk.Frame(self, style="Card.TFrame", padding=24, takefocus=0)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        self.header = ttk.Label(wrapper, text="Practice Prompt", style="H1.TLabel", takefocus=0)
        self.header.grid(row=0, column=0, sticky="w")

        self.sub = ttk.Label(
            wrapper,
            text="Press Start to reveal the problem. Use the 10 boxes only. Enter submits.",
            style="Sub.TLabel",
            wraplength=640,
            justify="left",
            takefocus=0,
        )
        self.sub.grid(row=1, column=0, sticky="w", pady=(6, 16))

        self.problem = ttk.Label(wrapper, text="", style="Problem.TLabel", wraplength=640, justify="left", takefocus=0)
        self.problem.grid(row=2, column=0, sticky="w")
        self.problem.grid_remove()

        # Grid of 1 x 10 single-character boxes
        grid = ttk.Frame(wrapper, style="Card.TFrame", padding=(0, 0, 0, 0), takefocus=0)
        grid.grid(row=3, column=0, sticky="w", pady=(14, 8))
        for c in range(10):
            grid.grid_columnconfigure(c, weight=0, minsize=56)

        # Register a validation command for single character
        vcmd = (self.register(self._validate_one_char), "%P")

        self.cells = []
        for idx in range(10):
            e = ttk.Entry(
                grid,
                width=2,
                justify="center",
                validate="key",
                validatecommand=vcmd,
                style="Cell.TEntry",
                font=("Inter", 16),
                takefocus=1,  # focusable
            )
            e.grid(row=0, column=idx, padx=(0 if idx == 0 else 8, 0), ipady=6)
            e.bind("<KeyRelease>", lambda ev, i=idx: self._auto_advance(ev, i))
            e.bind("<BackSpace>", lambda ev, i=idx: self._handle_backspace(ev, i))
            e.bind("<Left>", lambda ev, i=idx: self._move_focus(i - 1))
            e.bind("<Right>", lambda ev, i=idx: self._move_focus(i + 1))
            e.bind("<Up>", lambda ev: "break")
            e.bind("<Down>", lambda ev: "break")
            e.bind("<Tab>", lambda ev: "break")          # prevent leaving the 10 boxes with Tab
            e.bind("<Shift-Tab>", lambda ev: "break")
            self.cells.append(e)

        # Buttons row (only Start and Enter are clickable; after start, only Enter remains enabled)
        btns = ttk.Frame(wrapper, style="Card.TFrame", takefocus=0)
        btns.grid(row=4, column=0, sticky="e")

        self.start_btn = ttk.Button(btns, text="Start", style="Primary.TButton", command=self._start)
        self.start_btn.grid(row=0, column=0)

        self.submit_btn = ttk.Button(btns, text="Enter", style="Accent.TButton", command=self._submit)
        self.submit_btn.grid(row=0, column=1, padx=(8, 0))
        self.submit_btn.state(["disabled"])

        self.output = ttk.Label(wrapper, text="", style="Output.TLabel", takefocus=0)
        self.output.grid(row=5, column=0, sticky="w", pady=(12, 0))

        # Global Return key submits when enabled
        self.bind("<Return>", lambda e: self._submit())
        self.bind("<KP_Enter>", lambda e: self._submit())

        # Hide grid until start
        for e in self.cells:
            e.grid_remove()

    # ----- Actions -----
    def _start(self):
        self.problem.configure(text=PROBLEM_TEXT)
        self.problem.grid()
        for e in self.cells:
            e.delete(0, tk.END)
            e.grid()  # show
        self.submit_btn.state(["!disabled"])
        self.start_btn.state(["disabled"])
        self.output.configure(text="")
        self.cells[0].focus_set()

    def _submit(self):
        if "disabled" in self.submit_btn.state():
            return
        s = "".join(e.get()[:1] for e in self.cells)
        print(s)  # required: capture and print the response as a string
        self.output.configure(text=f"Captured: {s if s else '[empty]'}")

    # ----- Validation & Navigation -----
    def _validate_one_char(self, proposed: str):
        # allow at most 1 visible character; normalize to uppercase
        if len(proposed) <= 1:
            return True
        return False

    def _auto_advance(self, event, index: int):
        w: ttk.Entry = event.widget
        val = w.get()
        if val:
            # normalize to single uppercase char
            w.delete(0, tk.END)
            w.insert(0, val[-1].upper())
            # move to next cell if available
            self._move_focus(index + 1)

    def _handle_backspace(self, event, index: int):
        w: ttk.Entry = event.widget
        if w.get() == "":
            self._move_focus(index - 1)
            return "break"

    def _move_focus(self, index: int):
        if 0 <= index < len(self.cells):
            self.cells[index].focus_set()
        return "break"

    # ----- Style -----
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Palette
        bg = "#0f1224"
        card = "#171b34"
        text = "#e8eaf6"
        sub = "#b7bfd9"
        accent = "#6aa2ff"
        primary = "#8b5cf6"
        success = "#22c55e"

        self.configure(bg=bg)
        style.configure(".", background=card)
        style.configure("Card.TFrame", background=card)

        style.configure("H1.TLabel", background=card, foreground=text, font=("Inter", 20, "bold"))
        style.configure("Sub.TLabel", background=card, foreground=sub, font=("Inter", 11))
        style.configure("Problem.TLabel", background=card, foreground=text, font=("Inter", 13))
        style.configure("Output.TLabel", background=card, foreground=success, font=("Inter", 12, "bold"))

        style.configure("Cell.TEntry", fieldbackground="#0f1025", foreground=text, insertcolor=text, relief="flat")
        style.map("Cell.TEntry", fieldbackground=[("focus", "#0e1536")])

        base_btn = {"padding": (14, 8), "font": ("Inter", 11, "bold"), "relief": "flat"}
        style.configure("Primary.TButton", **base_btn, background=primary, foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#7c3aed")], foreground=[("disabled", "#9ca3af")])
        style.configure("Accent.TButton", **base_btn, background=accent, foreground="#0b1020")
        style.map("Accent.TButton", background=[("active", "#3b82f6")], foreground=[("disabled", "#6b7280")])

    # ----- Utils -----
    def _center_on_screen(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int((sw - w) / 2), int((sh - h) / 2.6)
        self.geometry(f"{w}x{h}+{x}+{y}")

if __name__ == "__main__":
    App().mainloop()
