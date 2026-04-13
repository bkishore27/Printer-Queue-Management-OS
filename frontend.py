import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time

# ── colour palette ───────────────────────────────────────────────────────────
BG_DARK        = "#0a0f1e"
BG_PANEL       = "#0d1630"
BG_CARD        = "#111d3c"
ACCENT_BLUE    = "#1e6fff"
ACCENT_CYAN    = "#00d4ff"
ACCENT_GLOW    = "#2979ff"
TEXT_PRIMARY   = "#e8f0fe"
TEXT_SECONDARY = "#7b9fd4"
TEXT_DIM       = "#3d5a8a"
SUCCESS        = "#00e5a0"
WARNING        = "#ffc453"
DANGER         = "#ff4d6d"
BORDER         = "#1c2f5e"

FONT_MONO    = ("Consolas", 10)
FONT_MONO_SM = ("Consolas", 9)
FONT_UI      = ("Segoe UI", 10)
FONT_UI_B    = ("Segoe UI", 10, "bold")
FONT_TITLE   = ("Segoe UI", 16, "bold")
FONT_LABEL   = ("Segoe UI", 9)

job_list    = []
job_counter = [1]

# ── helpers ──────────────────────────────────────────────────────────────────

def make_frame(parent, bg=BG_PANEL, **kw):
    return tk.Frame(parent, bg=bg, **kw)

def lbl(parent, text, font=FONT_UI, fg=TEXT_PRIMARY, bg=None, **kw):
    if bg is None:
        try:
            bg = parent.cget("bg")
        except Exception:
            bg = BG_DARK
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)

class StyledButton(tk.Label):
    def __init__(self, parent, text, command=None,
                 bg=ACCENT_BLUE, fg="white", hover_bg=ACCENT_GLOW,
                 font=FONT_UI_B, padx=18, pady=8, **kw):
        super().__init__(parent, text=text, font=font, fg=fg, bg=bg,
                         padx=padx, pady=pady, cursor="hand2", relief="flat", **kw)
        self._bg = bg; self._hov = hover_bg
        self.bind("<Enter>",    lambda e: self.config(bg=self._hov))
        self.bind("<Leave>",    lambda e: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: command() if command else None)

# ── root ─────────────────────────────────────────────────────────────────────

root = tk.Tk()
root.title("PrinterOS — Queue Management System")
root.configure(bg=BG_DARK)
try:
    root.state("zoomed")
except Exception:
    root.geometry("1300x820")

style = ttk.Style()
style.theme_use("clam")
style.configure("Tech.TCombobox",
                fieldbackground="#0a1628", background="#0a1628",
                foreground=TEXT_PRIMARY,
                selectbackground=ACCENT_BLUE, selectforeground="white",
                borderwidth=0)

# ── top bar ──────────────────────────────────────────────────────────────────

topbar = make_frame(root, bg=BG_PANEL)
topbar.pack(side="top", fill="x")
tk.Frame(topbar, bg=ACCENT_BLUE, width=4).pack(side="left", fill="y")
title_box = make_frame(topbar, bg=BG_PANEL)
title_box.pack(side="left", padx=20, pady=12)
lbl(title_box, "🖨  PrinterOS",
    font=FONT_TITLE, fg=TEXT_PRIMARY, bg=BG_PANEL).pack(side="left")
lbl(title_box, "  Queue Management System",
    font=("Segoe UI", 11), fg=TEXT_SECONDARY, bg=BG_PANEL).pack(side="left", padx=6)

sf = make_frame(topbar, bg=BG_PANEL)
sf.pack(side="right", padx=20)
status_dot = tk.Label(sf, text="●", font=("Segoe UI", 12), fg=SUCCESS, bg=BG_PANEL)
status_dot.pack(side="left")
status_lbl = tk.Label(sf, text=" READY", font=("Segoe UI", 9, "bold"), fg=SUCCESS, bg=BG_PANEL)
status_lbl.pack(side="left")

tk.Frame(root, bg=ACCENT_BLUE, height=2).pack(fill="x")

# ── status bar (pack bottom before body so it stays pinned) ──────────────────

statusbar = make_frame(root, bg="#060b18")
statusbar.pack(side="bottom", fill="x")
tk.Frame(statusbar, bg=BORDER, height=1).pack(fill="x")
status_msg = lbl(statusbar, "  Ready — add jobs and click Submit All to begin",
                 font=FONT_LABEL, fg=TEXT_DIM, bg="#060b18")
status_msg.pack(side="left", pady=5)

# ── body ─────────────────────────────────────────────────────────────────────

body = make_frame(root, bg=BG_DARK)
body.pack(fill="both", expand=True, padx=12, pady=10)

# ── LEFT panel ───────────────────────────────────────────────────────────────

left = make_frame(body, bg=BG_DARK)
left.pack(side="left", fill="both", expand=False, padx=(0, 8))
left.configure(width=360)
left.pack_propagate(False)

# --- Add Job card ---

def card_header(card_frame, title_text):
    hdr = make_frame(card_frame, bg=BG_CARD)
    hdr.pack(fill="x", padx=14, pady=(10, 6))
    lbl(hdr, title_text, font=FONT_UI_B, fg=ACCENT_CYAN, bg=BG_CARD).pack(side="left")
    tk.Frame(card_frame, bg=BORDER, height=1).pack(fill="x")
    inner = make_frame(card_frame, bg=BG_CARD)
    inner.pack(fill="x", padx=14, pady=10)
    return inner, hdr

add_card = tk.Frame(left, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
add_card.pack(fill="x", pady=(0, 10))

add_inner, add_hdr = card_header(add_card, "➕  New Print Job")

# Use a sub-frame with grid for the form fields
form = make_frame(add_inner, bg=BG_CARD)
form.pack(fill="x")
form.columnconfigure(0, weight=1)

def field_label(row, text):
    lbl(form, text.upper(), font=FONT_LABEL, fg=TEXT_SECONDARY, bg=BG_CARD).grid(
        row=row * 2, column=0, sticky="w", pady=(6, 2))

def text_entry(row):
    e = tk.Entry(form, bg="#0a1628", fg=TEXT_PRIMARY,
                 insertbackground=ACCENT_CYAN, relief="flat", font=FONT_UI, bd=0,
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT_BLUE)
    e.grid(row=row * 2 + 1, column=0, sticky="ew", ipady=7, pady=(0, 2))
    return e

def combo_entry(row, values):
    v = tk.StringVar()
    cb = ttk.Combobox(form, textvariable=v, values=values,
                      state="readonly", font=FONT_UI, style="Tech.TCombobox")
    cb.grid(row=row * 2 + 1, column=0, sticky="ew", ipady=4, pady=(0, 2))
    return v

field_label(0, "Job ID")
entry_job_id = text_entry(0)
entry_job_id.insert(0, str(job_counter[0]))

field_label(1, "Pages")
entry_pages = text_entry(1)

field_label(2, "Document Type")
category_var = combo_entry(2, ["1 — Newspaper", "2 — Magazine / Book", "3 — Advertisement"])

field_label(3, "Priority Level")
priority_var = combo_entry(3, ["1 — High", "2 — Medium", "3 — Low"])

# Add/Submit buttons
abf = make_frame(add_inner, bg=BG_CARD)
abf.pack(fill="x", pady=(12, 4))
StyledButton(abf, "＋  Add Job",    command=lambda: add_job(),
             bg=ACCENT_BLUE, hover_bg="#1458cc").pack(side="left",  fill="x", expand=True, padx=(0, 4), ipady=2)
StyledButton(abf, "🚀  Submit All", command=lambda: submit_all(),
             bg="#00994d",   hover_bg="#00bb5e").pack(side="left",  fill="x", expand=True, padx=(4, 0), ipady=2)

# --- Queue card ---

queue_card = tk.Frame(left, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
queue_card.pack(fill="both", expand=True)

q_hdr = make_frame(queue_card, bg=BG_CARD)
q_hdr.pack(fill="x", padx=14, pady=(10, 6))
lbl(q_hdr, "📋  Job Queue", font=FONT_UI_B, fg=ACCENT_CYAN, bg=BG_CARD).pack(side="left")
queue_count_lbl = lbl(q_hdr, "0 jobs", font=FONT_LABEL, fg=TEXT_DIM, bg=BG_CARD)
queue_count_lbl.pack(side="right")
tk.Frame(queue_card, bg=BORDER, height=1).pack(fill="x")

# column header
lbl(queue_card, "  # Job  │  Pages  │  Type          │  Priority",
    font=FONT_MONO_SM, fg=TEXT_DIM, bg="#080e1d").pack(fill="x")

lbx_frame = make_frame(queue_card, bg=BG_CARD)
lbx_frame.pack(fill="both", expand=True, padx=8, pady=(4, 4))

sb_jobs = tk.Scrollbar(lbx_frame, orient=tk.VERTICAL, bg=BG_PANEL,
                       troughcolor=BG_DARK, activebackground=ACCENT_BLUE,
                       highlightthickness=0, bd=0, width=10)
listbox_jobs = tk.Listbox(lbx_frame, yscrollcommand=sb_jobs.set,
                          font=FONT_MONO_SM, bg="#080e1d", fg=TEXT_PRIMARY,
                          selectbackground=ACCENT_BLUE, selectforeground="white",
                          activestyle="none", relief="flat", bd=0, highlightthickness=0)
sb_jobs.config(command=listbox_jobs.yview)
sb_jobs.pack(side="right", fill="y")
listbox_jobs.pack(side="left", fill="both", expand=True)

qbf = make_frame(queue_card, bg=BG_CARD)
qbf.pack(fill="x", padx=8, pady=(0, 10))
StyledButton(qbf, "🗑  Delete Selected", command=lambda: delete_selected(),
             bg="#5a2020", hover_bg=DANGER, font=FONT_UI).pack(
    side="left", fill="x", expand=True, padx=(0, 4), ipady=2)
StyledButton(qbf, "✕  Clear Queue", command=lambda: clear_queue(),
             bg="#3a2a10", hover_bg="#7a5a20", font=FONT_UI).pack(
    side="left", fill="x", expand=True, padx=(4, 0), ipady=2)

# ── RIGHT panel — console ─────────────────────────────────────────────────────

right = make_frame(body, bg=BG_DARK)
right.pack(side="left", fill="both", expand=True)

out_card = tk.Frame(right, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
out_card.pack(fill="both", expand=True)

out_hdr = make_frame(out_card, bg=BG_CARD)
out_hdr.pack(fill="x", padx=14, pady=(10, 6))
lbl(out_hdr, "⚙  Output Console", font=FONT_UI_B, fg=ACCENT_CYAN, bg=BG_CARD).pack(side="left")
tk.Frame(out_card, bg=BORDER, height=1).pack(fill="x")

txt_frame = make_frame(out_card, bg=BG_CARD)
txt_frame.pack(fill="both", expand=True, padx=(8, 0), pady=8)

out_sb = tk.Scrollbar(txt_frame, orient=tk.VERTICAL, bg=BG_PANEL,
                      troughcolor=BG_DARK, activebackground=ACCENT_BLUE,
                      highlightthickness=0, bd=0, width=10)
output_text = tk.Text(txt_frame, font=FONT_MONO,
                      bg="#05080f", fg=ACCENT_CYAN,
                      insertbackground=ACCENT_CYAN,
                      relief="flat", bd=0, highlightthickness=0,
                      wrap="word", state="disabled",
                      yscrollcommand=out_sb.set)
out_sb.config(command=output_text.yview)
out_sb.pack(side="right", fill="y")
output_text.pack(side="left", fill="both", expand=True)

output_text.tag_config("green",  foreground=SUCCESS)
output_text.tag_config("yellow", foreground=WARNING)
output_text.tag_config("red",    foreground=DANGER)
output_text.tag_config("cyan",   foreground=ACCENT_CYAN)
output_text.tag_config("dim",    foreground=TEXT_DIM)

obf = make_frame(out_card, bg=BG_CARD)
obf.pack(fill="x", padx=8, pady=(0, 10))
StyledButton(obf, "🗑  Clear Console", command=lambda: clear_output(),
             bg="#1a1a2e", hover_bg="#2d2d50", font=FONT_UI).pack(side="right", ipady=2)

# ── app logic ─────────────────────────────────────────────────────────────────

def set_status(msg, color=TEXT_DIM):
    status_msg.config(text=f"  {msg}", fg=color)

def append_output(text):
    def inner():
        output_text.config(state="normal")
        lo = text.lower()
        tag = None
        if "✅" in text or "success" in lo:              tag = "green"
        elif "⚠" in text or "warning" in lo or "full" in lo: tag = "yellow"
        elif "error" in lo or "invalid" in lo:            tag = "red"
        elif "🖨" in text or "printing" in lo:            tag = "cyan"
        elif text.strip().startswith(("==", "--", "──")): tag = "dim"
        ts = time.strftime("%H:%M:%S")
        output_text.insert(tk.END, f"[{ts}] ", "dim")
        output_text.insert(tk.END, text, tag or "")
        output_text.see(tk.END)
        output_text.config(state="disabled")
    root.after(0, inner)

def update_queue_count():
    n = len(job_list)
    queue_count_lbl.config(text=f"{n} job{'s' if n != 1 else ''}")

def add_job():
    job_id = entry_job_id.get().strip()
    pages  = entry_pages.get().strip()
    cat    = category_var.get().strip()
    pri    = priority_var.get().strip()

    if not all([job_id, pages, cat, pri]):
        messagebox.showwarning("Missing Fields", "Please fill all fields before adding a job.")
        return
    try:
        jid = int(job_id); pg = int(pages)
    except ValueError:
        messagebox.showerror("Invalid Input", "Job ID and Pages must be integers.")
        return
    if pg <= 0:
        messagebox.showerror("Invalid Input", "Pages must be a positive number.")
        return
    try:
        cat_num = int(cat.split("—")[0].strip())
        pri_num = int(pri.split("—")[0].strip())
    except Exception:
        messagebox.showerror("Parse Error", "Could not parse Category or Priority.")
        return

    job_list.append((jid, pg, cat_num, pri_num))
    cat_names = {1: "Newspaper", 2: "Magazine/Book", 3: "Ad"}
    pri_names = {1: "🔴 High", 2: "🟡 Med", 3: "🟢 Low"}
    listbox_jobs.insert(
        tk.END,
        f"  #{jid:>4}  │  {pg:>3}pp  │  {cat_names.get(cat_num,'?'):<13}│  {pri_names.get(pri_num,'?')}"
    )
    update_queue_count()
    set_status(f"Job #{jid} added to queue", ACCENT_CYAN)

    job_counter[0] += 1
    entry_job_id.delete(0, tk.END)
    entry_job_id.insert(0, str(job_counter[0]))
    entry_pages.delete(0, tk.END)
    category_var.set(""); priority_var.set("")

def delete_selected():
    sel = listbox_jobs.curselection()
    if not sel:
        messagebox.showinfo("No Selection", "Click a job in the queue to select it first.")
        return
    idx = sel[0]
    removed = job_list.pop(idx)
    listbox_jobs.delete(idx)
    update_queue_count()
    set_status(f"Job #{removed[0]} removed from queue", WARNING)

def clear_queue():
    if not job_list:
        return
    if messagebox.askyesno("Clear Queue", "Remove all pending jobs from the queue?"):
        job_list.clear()
        listbox_jobs.delete(0, tk.END)
        update_queue_count()
        set_status("Queue cleared", WARNING)

def clear_output():
    output_text.config(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.config(state="disabled")
    set_status("Console cleared")

def run_backend():
    root.after(0, lambda: set_status("Processing jobs…", ACCENT_CYAN))
    root.after(0, lambda: status_dot.config(fg=WARNING))
    root.after(0, lambda: status_lbl.config(text=" PRINTING", fg=WARNING))

    input_data = f"{len(job_list)}\n"
    for job in job_list:
        input_data += f"{job[0]}\n{job[1]}\n{job[2]}\n{job[3]}\n"

    job_list.clear()
    root.after(0, lambda: listbox_jobs.delete(0, tk.END))
    root.after(0, update_queue_count)

    try:
        process = subprocess.Popen(
            ["printer_queue.exe"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
        def read_pipe(pipe):
            for line in iter(pipe.readline, ""):
                append_output(line)
            pipe.close()
        threading.Thread(target=read_pipe, args=(process.stdout,), daemon=True).start()
        threading.Thread(target=read_pipe, args=(process.stderr,), daemon=True).start()
        process.stdin.write(input_data)
        process.stdin.close()
        process.wait()
        root.after(0, lambda: set_status("All jobs completed ✓", SUCCESS))
        root.after(0, lambda: status_dot.config(fg=SUCCESS))
        root.after(0, lambda: status_lbl.config(text=" READY", fg=SUCCESS))
    except FileNotFoundError:
        root.after(0, lambda: messagebox.showerror(
            "Backend Not Found",
            "printer_queue.exe was not found.\nMake sure it is compiled and placed in the same folder."))
        root.after(0, lambda: set_status("Backend not found", DANGER))
        root.after(0, lambda: status_dot.config(fg=DANGER))
        root.after(0, lambda: status_lbl.config(text=" ERROR", fg=DANGER))
    except Exception as ex:
        root.after(0, lambda: messagebox.showerror("Execution Error", str(ex)))
        root.after(0, lambda: set_status(f"Error: {ex}", DANGER))

def submit_all():
    if not job_list:
        messagebox.showwarning("Empty Queue", "Add at least one job before submitting.")
        return
    append_output(f"\n{'─'*60}\n")
    append_output(f"  Submitting {len(job_list)} job(s) to printer backend…\n")
    append_output(f"{'─'*60}\n\n")
    threading.Thread(target=run_backend, daemon=True).start()

def boot_msg():
    append_output("  PrinterOS — Queue Management System\n")
    append_output("  ─────────────────────────────────────────────────────────\n")
    append_output("  Add jobs in the left panel, then click  Submit All.\n")
    append_output("  Output from printer_queue.exe appears here in real-time.\n\n")

root.after(300, boot_msg)
root.mainloop()
