import asyncio
import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import zipfile
import psutil

# Optional Gemini SDK import for live AI briefings
try:
    from google import genai
    from google.genai import types
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
TELEMETRY_LOG = BASE_DIR / "mirage_telemetry.jsonl"
VACCINE_DIR = BASE_DIR / "generated_vaccines"
MANIFEST_FILE = VACCINE_DIR / "immunity_manifest.json"


def load_local_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


load_local_env()


class MirageDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Project Mirage-Ward | Ultimate Cyber Command Center")
        self.geometry("1280=800" if False else "1250x780")
        self.configure(bg="#0f172a")

        self.processes: dict[str, subprocess.Popen] = {}
        self.mitre_cells: dict[str, tk.Label] = {}
        self.mesh_nodes: list[int] = []

        # Initialize Gemini client if API key is present
        api_key = os.environ.get("GEMINI_API_KEY")
        self.ai_client = genai.Client(api_key=api_key) if (GEMINI_SDK_AVAILABLE and api_key) else None

        self.create_widgets()
        self.start_background_services()

        self.after(1000, self.poll_telemetry_logs)
        self.after(2000, self.poll_system_metrics)

    def create_widgets(self):
        # Header
        header = tk.Frame(self, bg="#1e293b", padx=15, pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="🛡️ PROJECT MIRAGE-WARD : ULTIMATE COMMAND CENTER",
            font=("Segoe UI", 13, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(side="left")

        self.status_lbl = tk.Label(
            header,
            text="● SYSTEM ARMED (AI LINKED)",
            font=("Segoe UI", 10, "bold"),
            fg="#4ade80" if self.ai_client else "#f59e0b",
            bg="#1e293b",
        )
        self.status_lbl.pack(side="right")

        # Notebook Tabs
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#0f172a", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1e293b", foreground="#cbd5e1", font=("Segoe UI", 9, "bold"), padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Operations & Live Feed
        tab_ops = tk.Frame(notebook, bg="#0f172a")
        notebook.add(tab_ops, text="  Operations & Telemetry  ")
        self.build_operations_tab(tab_ops)

        # Tab 2: MITRE ATT&CK Heatmap & Mesh Network
        tab_intel = tk.Frame(notebook, bg="#0f172a")
        notebook.add(tab_intel, text="  MITRE ATT&CK & Mesh Grid  ")
        self.build_intel_tab(tab_intel)

    def build_operations_tab(self, parent):
        main_pane = tk.PanedWindow(parent, orient="horizontal", bg="#0f172a", sashwidth=6)
        main_pane.pack(fill="both", expand=True, padx=5, pady=5)

        # Left Control Column
        left_frame = tk.Frame(main_pane, bg="#0f172a")
        main_pane.add(left_frame, width=380)

        # Modules
        mod_box = tk.LabelFrame(left_frame, text=" Defensive Modules ", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", padx=10, pady=8)
        mod_box.pack(fill="x", pady=(0, 8))
        self.mod_indicators = {}
        for name, script in [
            ("Trapdoor Shunt", "trapdoor_shunt.py"),
            ("Mirage Weaver", "mirage_weaver.py"),
            ("Auto-Vaccine Forge", "vaccine_forge.py"),
            ("Visual Aegis", "visual_aegis.py"),
            ("LDAP Honey-Schema", "ldap_honeypot.py"),
        ]:
            f = tk.Frame(mod_box, bg="#1e293b")
            f.pack(fill="x", pady=2)
            tk.Label(f, text=name, font=("Segoe UI", 9), fg="#cbd5e1", bg="#1e293b").pack(side="left")
            ind = tk.Label(f, text="ACTIVE", font=("Segoe UI", 8, "bold"), fg="#4ade80", bg="#1e293b")
            ind.pack(side="right")
            self.mod_indicators[script] = ind

        # Metrics
        metric_box = tk.LabelFrame(left_frame, text=" Host Telemetry ", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", padx=10, pady=8)
        metric_box.pack(fill="x", pady=(0, 8))
        self.cpu_lbl = tk.Label(metric_box, text="CPU Usage: 0.0%", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b")
        self.cpu_lbl.pack(anchor="w", pady=1)
        self.ram_lbl = tk.Label(metric_box, text="RAM Usage: 0.0%", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b")
        self.ram_lbl.pack(anchor="w", pady=1)
        self.threat_count_lbl = tk.Label(metric_box, text="Threats Neutralized: 0", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b")
        self.threat_count_lbl.pack(anchor="w", pady=(4, 1))

        # Controls
        action_box = tk.LabelFrame(left_frame, text=" Operator Controls ", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", padx=10, pady=8)
        action_box.pack(fill="x")

        tk.Button(action_box, text="🧪 Simulate Phishing Popup", command=self.run_simulated_popup, bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=5).pack(fill="x", pady=3)
        tk.Button(action_box, text="📦 Export Forensic IR Bundle (.zip)", command=self.export_forensic_bundle, bg="#0d9488", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=5).pack(fill="x", pady=3)
        tk.Button(action_box, text="📄 Export Executive PDF Report", command=self.export_pdf_report, bg="#4f46e5", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=5).pack(fill="x", pady=3)
        tk.Button(action_box, text="🚨 EMERGENCY LOCKDOWN", command=self.emergency_lockdown, bg="#dc2626", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", pady=5).pack(fill="x", pady=3)

        # Right Feed & AI Briefing Column
        right_frame = tk.Frame(main_pane, bg="#0f172a")
        main_pane.add(right_frame)

        # Gemini Tactical Briefing Box
        ai_box = tk.LabelFrame(right_frame, text=" 🧠 Gemini 3.8 Flash Tactical Analyst Briefing ", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b", padx=10, pady=8)
        ai_box.pack(fill="x", pady=(0, 8))
        self.ai_brief_lbl = tk.Label(ai_box, text="System armed. Waiting for intrusion telemetry...", font=("Segoe UI", 9), fg="#e2e8f0", bg="#1e293b", wraplength=750, justify="left")
        self.ai_brief_lbl.pack(fill="x")

        # Telemetry Log
        log_box = tk.LabelFrame(right_frame, text=" Live Forensic Incident Stream ", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b", padx=10, pady=8)
        log_box.pack(fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_box, wrap="word", bg="#020617", fg="#38bdf8", font=("Consolas", 9), insertbackground="white")
        self.log_text.pack(fill="both", expand=True)

    def build_intel_tab(self, parent):
        pane = tk.PanedWindow(parent, orient="vertical", bg="#0f172a", sashwidth=6)
        pane.pack(fill="both", expand=True, padx=10, pady=10)

        # Top: MITRE ATT&CK Matrix Heatmap
        mitre_box = tk.LabelFrame(pane, text=" MITRE ATT&CK Active Tactics Heatmap ", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#1e293b", padx=10, pady=10)
        pane.add(mitre_box, height=280)

        grid_frame = tk.Frame(mitre_box, bg="#1e293b")
        grid_frame.pack(fill="both", expand=True)

        tactics = [
            ("T1566: Phishing / BitB", "Visual Aegis"),
            ("T1059: Command Interpreter", "Mirage Weaver"),
            ("T1552: Unsecured Credentials", "Canary Honey-Token"),
            ("T1078: Valid Accounts", "Session Shunt"),
            ("T1562: Impair Defenses", "Process Freeze"),
            ("T1486: Data Encrypted for Impact", "Auto-Vaccine Forge"),
        ]

        for i, (tactic, desc) in enumerate(tactics):
            row, col = divmod(i, 3)
            cell = tk.Frame(grid_frame, bg="#0f172a", bd=1, relief="solid", padx=10, pady=10)
            cell.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            grid_frame.grid_columnconfigure(col, weight=1)
            grid_frame.grid_rowconfigure(row, weight=1)

            lbl_title = tk.Label(cell, text=tactic, font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#0f172a")
            lbl_title.pack(anchor="w")
            lbl_sub = tk.Label(cell, text=f"Sensor: {desc}", font=("Segoe UI", 8), fg="#64748b", bg="#0f172a")
            lbl_sub.pack(anchor="w")
            
            self.mitre_cells[tactic] = cell

        ## Bottom: Peer Mesh Network Canvas
        mesh_box = tk.LabelFrame(pane, text=" Distributed Peer Immunity Mesh Network ", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#1e293b", padx=10, pady=10)
        pane.add(mesh_box)

        self.canvas = tk.Canvas(mesh_box, bg="#020617", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.draw_mesh_network()

    def draw_mesh_network(self):
        self.canvas.delete("all")
        w, h = 800, 300
        center_x, center_y = 350, 120
        peers = [(120, 60), (120, 180), (580, 60), (580, 180)]

        for px, py in peers:
            self.canvas.create_line(center_x, center_y, px, py, fill="#334155", width=2, dash=(4, 4))
            self.canvas.create_oval(px-24, py-24, px+24, py+24, fill="#1e293b", outline="#38bdf8", width=2)
            self.canvas.create_text(px, py, text="SIEM Peer", fill="#94a3b8", font=("Segoe UI", 8))

        self.canvas.create_oval(center_x-35, center_y-35, center_x+35, center_y+35, fill="#0284c7", outline="#38bdf8", width=3)
        self.canvas.create_text(center_x, center_y, text="MIRAGE\nHUB", fill="white", font=("Segoe UI", 9, "bold"), justify="center")

    def pulse_mesh_network(self):
        center_x, center_y = 350, 120
        peers = [(120, 60), (120, 180), (580, 60), (580, 180)]
        for px, py in peers:
            pulse = self.canvas.create_oval(center_x-6, center_y-6, center_x+6, center_y+6, fill="#4ade80", outline="")
            
            def animate(p_id, x1, y1, x2, y2, step=0):
                if step > 20:
                    self.canvas.delete(p_id)
                    return
                cur_x = x1 + (x2 - x1) * (step / 20)
                cur_y = y1 + (y2 - y1) * (step / 20)
                self.canvas.coords(p_id, cur_x-6, cur_y-6, cur_x+6, cur_y+6)
                self.after(30, lambda: animate(p_id, x1, y1, x2, y2, step+1))
            
            animate(pulse, center_x, center_y, px, py)

    def start_background_services(self):
        scripts = ["trapdoor_shunt.py", "mirage_weaver.py", "vaccine_forge.py", "visual_aegis.py", "ldap_honeypot.py"]
        for script in scripts:
            script_path = BASE_DIR / script
            if script_path.exists():
                try:
                    p = subprocess.Popen(["start", "cmd", "/k", "python", str(script_path)], shell=True)
                    self.processes[script] = p
                except Exception as e:
                    pass

    def poll_telemetry_logs(self):
        if TELEMETRY_LOG.exists():
            try:
                with open(TELEMETRY_LOG, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    self.threat_count_lbl.config(text=f"Threats Neutralized: {len(lines)}")
                    recent = lines[-15:]
                    self.log_text.delete("1.0", tk.END)
                    self.log_text.insert(tk.END, f"[*] Monitoring telemetry ({len(lines)} total events recorded)...\n\n")
                    
                    last_cmd = ""
                    for line in recent:
                        try:
                            data = json.loads(line.strip())
                            ts = data.get("timestamp", "").split("T")[-1][:8]
                            cmd = data.get("command", "")
                            src = data.get("source", "")
                            last_cmd = cmd
                            self.log_text.insert(tk.END, f"[{ts}] SOURCE {src} -> {cmd}\n")
                            
                            if "[VISUAL-SPOOF]" in cmd:
                                self.illuminate_mitre("T1566: Phishing / BitB")
                            elif "aws_prod_keys.env" in cmd or "network_passwords.txt" in cmd:
                                self.illuminate_mitre("T1552: Unsecured Credentials")
                            elif "[LDAP-RECON]" in cmd:
                                self.illuminate_mitre("T1078: Valid Accounts")
                            else:
                                self.illuminate_mitre("T1059: Command Interpreter")
                        except Exception:
                            pass

                    if last_cmd and self.ai_client:
                        self.update_ai_briefing(last_cmd)
            except Exception:
                pass

        self.after(1500, self.poll_telemetry_logs)

    def illuminate_mitre(self, tactic_key: str):
        if tactic_key in self.mitre_cells:
            cell = self.mitre_cells[tactic_key]
            cell.configure(bg="#7f1d1d")
            for child in cell.winfo_children():
                child.configure(bg="#7f1d1d", fg="#fca5a5")
            self.pulse_mesh_network()

    def update_ai_briefing(self, latest_event: str):
        def call_gemini():
            try:
                resp = self.ai_client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=f"Summarize this cybersecurity intrusion event in 1 sharp, professional tactical sentence for a SOC operator: {latest_event}"
                )
                if resp and resp.text:
                    self.ai_brief_lbl.config(text=resp.text.strip())
            except Exception:
                pass
        import threading
        threading.Thread(target=call_gemini, daemon=True).start()

    def poll_system_metrics(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        self.cpu_lbl.config(text=f"CPU Usage: {cpu}%")
        self.ram_lbl.config(text=f"RAM Usage: {ram}%")
        self.after(2000, self.poll_system_metrics)

    def run_simulated_popup(self):
        script_path = BASE_DIR / "visual_aegis.py"
        if script_path.exists():
            subprocess.Popen([sys.executable, str(script_path), "--simulate-popup"])
            self.log_text.insert(tk.END, "[*] Triggered simulated BitB phishing popup test.\n")

    def export_forensic_bundle(self):
        zip_path = BASE_DIR / "MirageWard_Forensic_Evidence.zip"
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                if TELEMETRY_LOG.exists():
                    zf.write(TELEMETRY_LOG, arcname="mirage_telemetry.jsonl")
                if MANIFEST_FILE.exists():
                    zf.write(MANIFEST_FILE, arcname="immunity_manifest.json")
                if VACCINE_DIR.exists():
                    for y_file in VACCINE_DIR.glob("*.yar"):
                        zf.write(y_file, arcname=f"yara_rules/{y_file.name}")
            messagebox.showinfo("Forensic Bundle Exported", f"Successfully packaged all evidence into:\n{zip_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export bundle: {e}")

    def export_pdf_report(self):
        """Triggers the PDF incident report generator script."""
        script_path = BASE_DIR / "pdf_report_generator.py"
        if script_path.exists():
            try:
                subprocess.Popen([sys.executable, str(script_path)])
                messagebox.showinfo("PDF Report Generated", "Executive PDF incident report compiled successfully as 'MirageWard_Incident_Report.pdf'!")
                self.log_text.insert(tk.END, "[*] Executive PDF incident report compiled.\n")
            except Exception as e:
                messagebox.showerror("PDF Error", f"Failed to generate PDF report: {e}")
        else:
            messagebox.showwarning("Missing Script", "Please make sure pdf_report_generator.py is saved in your project folder.")

    def emergency_lockdown(self):
        if messagebox.askyesno("Emergency Lockdown", "Shut down all defense modules?"):
            for script, p in self.processes.items():
                try:
                    p.terminate()
                except Exception:
                    pass
            self.status_lbl.config(text="● SYSTEM DISARMED", fg="#ef4444")

    def destroy(self):
        for script, p in self.processes.items():
            try:
                p.terminate()
            except Exception:
                pass
        super().destroy()


if __name__ == "__main__":
    app = MirageDashboard()
    app.mainloop()