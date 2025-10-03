import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime

APP_TITLE = "CPU Scheduling Practice — Guided Flow (v6)"

# ----- Problem specification (fixed for this app) -----
PROCESSES = [
    {"name": "A", "arrival": 0, "service": 10},
    {"name": "B", "arrival": 2, "service": 5},
    {"name": "C", "arrival": 2, "service": 7},
    {"name": "D", "arrival": 5, "service": 3},
    {"name": "E", "arrival": 11, "service": 1},
]
TOTAL_SERVICE = sum(p["service"] for p in PROCESSES)  # 26
HORIZON = TOTAL_SERVICE

RR_QUANTUM = 2
MLFQ_Q0 = 1
MLFQ_Q1 = 2
MLFQ_Q2 = 4

OVERALL_STATEMENT = (
    "Scheduling Problem — Overview\n\n"
    "You are given 5 processes A–E with the following arrival (start) and service (burst) times.\n"
    "If multiple processes arrive at the same time, break ties alphabetically (A before B before C, etc.).\n\n"
    "Processes:\n"
    f"  A: arrival={PROCESSES[0]['arrival']}, service={PROCESSES[0]['service']}\n"
    f"  B: arrival={PROCESSES[1]['arrival']}, service={PROCESSES[1]['service']}\n"
    f"  C: arrival={PROCESSES[2]['arrival']}, service={PROCESSES[2]['service']}\n"
    f"  D: arrival={PROCESSES[3]['arrival']}, service={PROCESSES[3]['service']}\n"
    f"  E: arrival={PROCESSES[4]['arrival']}, service={PROCESSES[4]['service']}\n\n"
    "Task:\n"
    f"Across several scheduling policies, fill in which process runs during each CPU time unit t=0..{HORIZON-1}. "
    "Enter the letter A–E in each box. Leave a box blank only if the CPU is idle.\n\n"
    "Begin with FIFO when ready."
)

POLICY_ORDER = ["FIFO", "RRq2", "STCF", "MLFQ"]
POLICY_TITLES = {
    "FIFO": "Problem 1 — FIFO (FCFS)",
    "RRq2": f"Problem 2 — Round Robin (q = {RR_QUANTUM})",
    "STCF": "Problem 3 — STCF",
    "MLFQ": f"Problem 4 — MLFQ (Q0={MLFQ_Q0}, Q1={MLFQ_Q1}, Q2={MLFQ_Q2})",
}
POLICY_HELP = {
    "FIFO": (
        "Run processes in order of arrival; never preempt the running process. "
        "On ties at arrival, earlier in the alphabet enters the queue first."
    ),
    "RRq2": (
        f"Round Robin: quantum = {RR_QUANTUM}. Preempt on quantum expiry and enqueue at tail. "
        "On ties at arrival, enqueue in alphabetical order."
    ),
    "STCF": (
        "Preemptive shortest-time-to-completion-first. "
        "At every time unit, run the available job with the smallest remaining time; break ties alphabetically."
    ),
    "MLFQ": (
        f"Three queues with increasing time quanta. Q0={MLFQ_Q0}, Q1={MLFQ_Q1}, Q2={MLFQ_Q2}. "
        "New arrivals enter Q0. Always run from the highest non-empty queue. "
        "On quantum expiry, demote to the next lower queue. On I/O/voluntary yield, keep level. "
        "Break ties alphabetically on arrival/queue entry."
    ),
}

# ----- Shared widget pieces -----

def is_allowed_char(s: str) -> bool:
    """Allow only '', 'A'..'E' (case-insensitive)."""
    if s == "":
        return True
    if len(s) == 1 and s.upper() in ("A", "B", "C", "D", "E"):
        return True
    return False


class TimelineGrid(ttk.Frame):
    """A scrollable single-row grid of HORIZON cells labeled by time t=0..HORIZON-1."""

    def __init__(self, master, horizon: int, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        # Horizontal scrollable canvas
        self.canvas = tk.Canvas(self, highlightthickness=0, height=120, background="#F3F4F8")
        self.scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scroll_x.set)

        self.inner = ttk.Frame(self.canvas, style="Card.TFrame")
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.grid(row=0, column=0, sticky="ew")
        self.scroll_x.grid(row=1, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)

        self.cells = []
        self.labels = []

        # Validation: only A..E or empty; 1 char max
        vcmd = (self.register(self._validate_cell), "%P")

        # Build time labels and entry cells
        for t in range(horizon):
            col = t
            lbl = ttk.Label(self.inner, text=str(t), style="Time.TLabel", padding=(2, 2))
            lbl.grid(row=0, column=col, padx=(6 if t == 0 else 8, 0), pady=(2, 0), sticky="n")
            self.labels.append(lbl)

            e = ttk.Entry(
                self.inner,
                width=2,
                justify="center",
                validate="key",
                validatecommand=vcmd,
                style="Cell.TEntry",
                font=("Segoe UI", 16),
            )
            e.grid(row=1, column=col, padx=(6 if t == 0 else 8, 0), ipady=6, pady=(2, 10))
            e.bind("<KeyRelease>", lambda ev, i=t: self._on_keyrelease(ev, i))
            e.bind("<BackSpace>", lambda ev, i=t: self._handle_backspace(ev, i))
            e.bind("<Left>", lambda ev, i=t: self._move_focus(i - 1))
            e.bind("<Right>", lambda ev, i=t: self._move_focus(i + 1))
            e.bind("<Up>", lambda ev: "break")
            e.bind("<Down>", lambda ev: "break")
            self.cells.append(e)

        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_scroll)

    def focus_first(self):
        if self.cells:
            self.cells[0].focus_set()

    def get_string(self):
        return "".join(e.get()[:1].upper() for e in self.cells)

    # ----- Validation / navigation -----
    def _validate_cell(self, proposed: str):
        if len(proposed) > 1:
            return False
        return is_allowed_char(proposed)

    def _on_keyrelease(self, event, index: int):
        w: ttk.Entry = event.widget
        val = w.get()
        if val:
            w.delete(0, tk.END)
            w.insert(0, val[-1].upper())

        ch = event.char
        if ch and ch.isalpha() and ch.upper() in ("A", "B", "C", "D", "E"):
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

    def _on_shift_scroll(self, event):
        self.canvas.xview_scroll(-1 if event.delta > 0 else 1, "units")


def make_proc_table(parent):
    """A compact table with Process / Arrival / Service as a ttk.Treeview."""
    tv = ttk.Treeview(parent, columns=("name", "arrival", "service"), show="headings", height=5, style="Light.Treeview")
    tv.heading("name", text="Process")
    tv.heading("arrival", text="Arrival")
    tv.heading("service", text="Service")
    tv.column("name", width=90, anchor="center")
    tv.column("arrival", width=90, anchor="center")
    tv.column("service", width=90, anchor="center")
    for p in PROCESSES:
        tv.insert("", "end", values=(p["name"], p["arrival"], p["service"]))
    return tv


class ScrollFrame(ttk.Frame):
    """Reusable vertical scrollable frame."""
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, background="#F6F8FE")
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.inner = ttk.Frame(self.canvas, style="Card.TFrame")
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel support (Windows/macOS)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)      # Windows
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)  # Linux up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)  # Linux down

    def _on_inner_configure(self, _ev):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, ev):
        self.canvas.itemconfig(self.inner_id, width=ev.width)

    def _on_mousewheel(self, ev):
        # Typical delta is multiples of 120 on Windows/macOS
        self.canvas.yview_scroll(int(-ev.delta/120), "units")

    def _on_mousewheel_linux(self, ev):
        if ev.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif ev.num == 5:
            self.canvas.yview_scroll(1, "units")


# ----- Page classes -----

class BasePage(ttk.Frame):
    def __init__(self, master, app, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.app = app


class StartPage(BasePage):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.columnconfigure(0, weight=1)

        title = ttk.Label(self, text="CPU Scheduling — Guided Practice", style="H1.TLabel")
        title.grid(row=0, column=0, sticky="w")

        statement = ttk.Label(self, text=OVERALL_STATEMENT, style="Problem.TLabel", wraplength=980, justify="left")
        statement.grid(row=1, column=0, sticky="w", pady=(8, 18))

        start_btn = ttk.Button(self, text="Start — FIFO", style="Primary.TButton",
                               command=lambda: self.app.goto_policy("FIFO"))
        start_btn.grid(row=2, column=0, sticky="w")


class PolicyPage(BasePage):
    def __init__(self, master, app, policy_key: str):
        super().__init__(master, app)
        self.policy_key = policy_key
        self.columnconfigure(0, weight=1)

        title = ttk.Label(self, text=POLICY_TITLES[policy_key], style="H1.TLabel")
        title.grid(row=0, column=0, sticky="w")

        help_lbl = ttk.Label(self, text=POLICY_HELP[policy_key], style="Help.TLabel", wraplength=980, justify="left")
        help_lbl.grid(row=1, column=0, sticky="w", pady=(6, 8))

        # Process table
        table = make_proc_table(self)
        table.grid(row=2, column=0, sticky="w", pady=(0, 10))

        self.grid_frame = TimelineGrid(self, horizon=HORIZON)
        self.grid_frame.grid(row=3, column=0, sticky="ew")

        btn_row = ttk.Frame(self)
        btn_row.grid(row=4, column=0, sticky="e", pady=(12, 0))

        submit_btn = ttk.Button(btn_row, text="Submit", style="Accent.TButton", command=self._submit)
        submit_btn.grid(row=0, column=0, padx=(0, 8))

        self.msg = ttk.Label(self, text="", style="Output.TLabel")
        self.msg.grid(row=5, column=0, sticky="w", pady=(10, 0))

        self.bind_all("<Return>", self._on_return)
        self.after(50, self.grid_frame.focus_first)

    def _on_return(self, _ev):
        if self.focus_get() is not None and str(self.focus_get()).startswith(str(self)):
            self._submit()

    def _submit(self):
        s = self.grid_frame.get_string()
        self.app.responses[self.policy_key] = s
        self.msg.configure(text=f"Submission saved ({len(s)} chars).")
        self.app.goto_survey(self.policy_key)


class SurveyPage(BasePage):
    """Scrollable survey page with 3 LLM explanations + ratings and one overall comment."""

    def __init__(self, master, app, policy_key: str):
        super().__init__(master, app)
        self.policy_key = policy_key
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=f"{POLICY_TITLES[policy_key]} — Explanations & Survey", style="H1.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        # Scrollable content
        sf = ScrollFrame(self)
        sf.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.rowconfigure(1, weight=1)

        content = sf.inner

        # Three LLM responses + Likert ratings
        self.llm_texts = []
        self.rating_vars = []

        for i in range(3):
            section = ttk.LabelFrame(content, text=f"LLM Response {i+1}", style="Light.TLabelframe")
            section.grid(row=i*2, column=0, sticky="nsew", pady=(0, 10), padx=2)
            section.columnconfigure(0, weight=1)

            txt = tk.Text(section, height=6, wrap="word", bg="#FFFFFF", fg="#0B1220")
            txt.insert("1.0", f"Paste or type explanation {i+1} here.")
            txt.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
            self.llm_texts.append(txt)

            prompt = ttk.Label(section, text="How close is this explanation to accurately identifying your misconception? (1=Not close, 7=Exactly right)", style="Help.TLabel")
            prompt.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))

            rv = tk.IntVar(value=0)
            self.rating_vars.append(rv)
            likert = ttk.Frame(section)
            likert.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 8))
            for j in range(1, 8):
                ttk.Radiobutton(likert, text=str(j), value=j, variable=rv).grid(row=0, column=j-1, padx=6)

        # One open-ended feedback
        fb_lbl = ttk.Label(content, text="Overall comments on the explanations:", style="Help.TLabel")
        fb_lbl.grid(row=6, column=0, sticky="w", pady=(4, 4), padx=2)

        self.fb_text = tk.Text(content, height=6, wrap="word", bg="#FFFFFF", fg="#0B1220")
        self.fb_text.grid(row=7, column=0, sticky="ew", padx=2)

        # Buttons pinned at bottom of scrollable content
        btns = ttk.Frame(content)
        btns.grid(row=8, column=0, sticky="e", pady=(12, 8))
        ttk.Button(btns, text="Save & Continue ▶", style="Primary.TButton", command=self._save_and_continue).grid(
            row=0, column=0
        )

    def _save_and_continue(self):
        llms = [t.get("1.0", "end-1c") for t in self.llm_texts]
        ratings = [rv.get() for rv in self.rating_vars]
        feedback = self.fb_text.get("1.0", "end-1c")

        self.app.surveys[self.policy_key] = {
            "llm_texts": llms,
            "ratings": ratings,
            "feedback": feedback,
        }

        idx = POLICY_ORDER.index(self.policy_key)
        if idx < len(POLICY_ORDER) - 1:
            self.app.goto_policy(POLICY_ORDER[idx + 1])
        else:
            self.app.goto_summary()


class SummaryPage(BasePage):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="Summary — Collected Work", style="H1.TLabel").grid(row=0, column=0, sticky="w")

        self.text = tk.Text(self, height=20, wrap="word", bg="#FFFFFF", fg="#0B1220")
        self.text.grid(row=1, column=0, sticky="nsew", pady=(8, 10))
        self.rowconfigure(1, weight=1)

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, sticky="e")

        ttk.Button(btns, text="Save Master TXT", style="Primary.TButton",
                   command=self._save_master_txt).grid(row=0, column=0)

        self.refresh()

    def refresh(self):
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, self.app.format_master_txt())

    def _save_master_txt(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="scheduling_master.txt"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.app.format_master_txt())
        messagebox.showinfo("Saved", f"Saved to:\n{path}")


# ----- App -----

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg="#E8ECF6")
        self._center_on_screen(1100, 820)
        self._build_style()

        # App state
        self.responses = {}  # policy_key -> timeline string
        self.surveys = {}    # policy_key -> dict(llm_texts, ratings, feedback)

        # Main container card
        self.card = ttk.Frame(self, style="Card.TFrame", padding=24)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.columnconfigure(0, weight=1)
        self.card.rowconfigure(0, weight=1)

        # Start
        self.current_page = None
        self.goto_start()

        self.save_dir = os.getcwd()

    # Navigation helpers
    def _set_page(self, widget: ttk.Frame):
        if self.current_page is not None:
            self.current_page.destroy()
        self.current_page = widget
        self.current_page.grid(row=0, column=0, sticky="nsew")

    def goto_start(self):
        self._set_page(StartPage(self.card, self))

    def goto_policy(self, policy_key: str):
        self._set_page(PolicyPage(self.card, self, policy_key))

    def goto_survey(self, policy_key: str):
        self._set_page(SurveyPage(self.card, self, policy_key))

    def goto_summary(self):
        page = SummaryPage(self.card, self)
        self._set_page(page)

    # Formatting helpers for TXT (single file at end)
    def format_master_txt(self) -> str:
        out = []
        out.append("CPU Scheduling Practice — Master Record\n")
        out.append("Processes (Arrival, Service):")
        for p in PROCESSES:
            out.append(f"  {p['name']}: arrival={p['arrival']}, service={p['service']}")
        out.append("")
        for key in POLICY_ORDER:
            s = self.responses.get(key, "")
            out.append(f"[{key}] timeline len={len(s)}")
            out.append(s)
            survey = self.surveys.get(key)
            if survey:
                for i, (txt, r) in enumerate(zip(survey.get("llm_texts", []), survey.get("ratings", [])), start=1):
                    out.append(f"[{key}] LLM {i}:")
                    out.append((txt or "").strip())
                    out.append(f"[{key}] Rating {i}: {r} (misconception closeness)")
                out.append(f"[{key}] Overall feedback:")
                out.append((survey.get('feedback') or "").strip())
            out.append("")
        return "\n".join(out)

    # Style
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Light palette with high contrast
        bg = "#E8ECF6"        # window background
        card = "#F6F8FE"      # card background
        text = "#0B1220"      # primary text
        sub = "#24324D"       # secondary text
        accent = "#2563EB"    # accent blue
        primary = "#7C3AED"   # primary purple

        self.configure(bg=bg)
        style.configure(".", background=card, foreground=text, font=("Segoe UI", 11))
        style.configure("Card.TFrame", background=card)

        style.configure("H1.TLabel", background=card, foreground=text, font=("Segoe UI", 22, "bold"))
        style.configure("H2.TLabel", background=card, foreground=text, font=("Segoe UI", 16, "bold"))
        style.configure("Problem.TLabel", background=card, foreground=text, font=("Segoe UI", 12))
        style.configure("Help.TLabel", background=card, foreground=sub, font=("Segoe UI", 11))
        style.configure("Time.TLabel", background=card, foreground=sub, font=("Segoe UI", 9))
        style.configure("Output.TLabel", background=card, foreground="#065F46", font=("Segoe UI", 12, "bold"))

        style.configure("Cell.TEntry", fieldbackground="#FFFFFF", foreground=text, insertcolor=text, relief="solid")
        style.map("Cell.TEntry", fieldbackground=[("focus", "#FFFFFF")])

        style.configure("Light.Treeview",
                        background="#FFFFFF", fieldbackground="#FFFFFF", foreground=text, bordercolor="#CBD5E1")
        style.map("Light.Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", text)])

        style.configure("Light.TLabelframe", background=card, foreground=sub)
        style.configure("Light.TLabelframe.Label", background=card, foreground=sub)

        base_btn = {"padding": (14, 8), "font": ("Segoe UI", 11, "bold"), "relief": "flat"}
        style.configure("Primary.TButton", **base_btn, background=primary, foreground="#FFFFFF")
        style.map("Primary.TButton", background=[("active", "#6D28D9")], foreground=[("disabled", "#9CA3AF")])
        style.configure("Accent.TButton", **base_btn, background=accent, foreground="#FFFFFF")
        style.map("Accent.TButton", background=[("active", "#1D4ED8")], foreground=[("disabled", "#6B7280")])

    def _center_on_screen(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int((sw - w) / 2), int((sh - h) / 2.6)
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    App().mainloop()
