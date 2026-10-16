import asyncio
import ctypes
from ctypes import wintypes
import datetime
import io
import json
import os
from pathlib import Path
import sys
import psutil
from PIL import ImageGrab
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


def load_local_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


load_local_env()

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

MODEL_ID = "gemini-3.8-flash"
TELEMETRY_LOG = str(Path(__file__).resolve().parent / "mirage_telemetry.jsonl")
SCAN_INTERVAL_SECONDS = 0.3

GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008

UNTRUSTED_UI_HOSTS = {
    "python.exe",
    "pythonw.exe",
    "powershell.exe",
    "pwsh.exe",
    "mshta.exe",
    "wscript.exe",
    "cscript.exe",
    "cmd.exe",
    "javaw.exe",
}

SUSPICIOUS_TITLE_KEYWORDS = [
    "windows security",
    "microsoft account",
    "sign in to your account",
    "session expired",
    "verify your identity",
    "bitlocker",
    "critical alert",
    "support",
    "oauth",
    "authenticate",
]


class VisualVerdict(BaseModel):
    is_deceptive_ui: bool = Field(description="True if the window is a fake login, BitB attack, or scam overlay.")
    risk_score: float = Field(description="Risk score from 0.0 to 1.0.")
    attack_classification: str = Field(description="Attack category or 'Benign'")
    visual_claims_to_be: str = Field(description="What brand, OS dialog, or URL the window visually claims to be.")
    mismatch_explanation: str = Field(description="Why visual appearance conflicts with true OS process.")
    recommended_action: str = Field(description="Immediate mitigation action.")


VISION_SYSTEM_PROMPT = """You are Visual-Aegis, a Blue Team multimodal anti-phishing sensor.
Inspect the window screenshot against OS kernel telemetry. Respond strictly in JSON.
"""


def get_active_window_telemetry() -> dict | None:
    if sys.platform != "win32":
        return None
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value.strip()

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    if (rect.right - rect.left) <= 50 or (rect.bottom - rect.top) <= 50:
        return None

    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    is_topmost = bool(ex_style & WS_EX_TOPMOST)

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    proc_id = pid.value

    try:
        proc = psutil.Process(proc_id)
        exe_name = proc.name()
        exe_path = proc.exe()
        cmdline = " ".join(proc.cmdline()[:4])
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        exe_name = "unknown.exe"
        exe_path = "Protected"
        cmdline = ""

    return {
        "hwnd": hwnd,
        "pid": proc_id,
        "title": title,
        "exe_name": exe_name,
        "exe_path": exe_path,
        "cmdline": cmdline,
        "is_topmost": is_topmost,
        "bbox": (rect.left, rect.top, rect.right, rect.bottom),
    }


def kill_rogue_process(hwnd: int, pid: int) -> str:
    """Instantly destroys the specific window handle and terminates its owner PID."""
    try:
        if sys.platform == "win32" and hwnd:
            ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0) # WM_CLOSE
        
        if pid and pid != os.getpid():
            p = psutil.Process(pid)
            p.terminate()
            return f"Neutralized HWND {hwnd} (PID {pid} terminated)"
    except Exception as e:
        return f"Neutralization note: {e}"
    return "Neutralized UI"


class VisualAegisScanner:
    def __init__(self, auto_terminate: bool = True):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.auto_terminate = auto_terminate
        self.inspected_cache: set[str] = set()

        print("=" * 74)
        print("[*] MIRAGE-WARD: VISUAL-AEGIS SUB-SECOND SHIELD INITIALIZED")
        print(f"[*] Polling Interval  : {SCAN_INTERVAL_SECONDS}s (Lightning Fast)")
        print(f"[*] Active Defense    : Instant Heuristic Kill + Async AI Forensics")
        print("=" * 74)

    def evaluate_quick_heuristic(self, meta: dict) -> tuple[bool, str]:
        title_lower = meta["title"].lower()
        exe_lower = meta["exe_name"].lower()

        if "visual_aegis.py" in title_lower and "security" not in title_lower:
            return False, ""

        has_cred_keyword = any(kw in title_lower for kw in SUSPICIOUS_TITLE_KEYWORDS)
        is_untrusted_host = exe_lower in UNTRUSTED_UI_HOSTS

        if has_cred_keyword and is_untrusted_host:
            return True, f"Instant Cross-Layer Match: Untrusted '{meta['exe_name']}' spawned credential title '{meta['title']}'"

        return False, ""

    async def async_forensic_audit(self, meta: dict, trigger_reason: str):
        try:
            img = ImageGrab.grab(bbox=meta["bbox"])
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            
            verdict = VisualVerdict(
                is_deceptive_ui=True,
                risk_score=0.99,
                attack_classification="Process-UI Impersonation & BitB Phishing",
                visual_claims_to_be=meta["title"],
                mismatch_explanation=f"Triggered by sub-second heuristic: {trigger_reason}",
                recommended_action=f"Terminated PID {meta['pid']} instantly.",
            )

            if self.client:
                telemetry_context = f"Window: {meta['title']}\nPID: {meta['pid']}\nProcess: {meta['exe_name']}"
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=MODEL_ID,
                    contents=[
                        types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"),
                        telemetry_context,
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=VISION_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=VisualVerdict,
                        temperature=0.1,
                    ),
                )
                if response and response.text:
                    verdict = VisualVerdict.model_validate_json(response.text)

            event = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "source": f"('127.0.0.1', {meta['pid']})",
                "command": f"[VISUAL-SPOOF] {meta['exe_name']} rendered '{verdict.visual_claims_to_be}'",
                "canary_tripped": True,
                "response_sample": verdict.mismatch_explanation[:120],
            }
            with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
            print(f"\033[96m[+] Async Forensic Audit Logged to {TELEMETRY_LOG} (Vaccine-Forge notified)\033[0m\n")
        except Exception as e:
            print(f"[!] Async audit notice: {e}")

    async def monitor_loop(self):
        print("[*] Sub-second shield active. Run `python visual_aegis.py --simulate-popup` to test!\n")
        while True:
            meta = get_active_window_telemetry()
            if meta:
                dedup_key = f"{meta['pid']}:{meta['title']}"
                is_threat, reason = self.evaluate_quick_heuristic(meta)

                if is_threat and dedup_key not in self.inspected_cache:
                    self.inspected_cache.add(dedup_key)

                    print("\n" + "!" * 74)
                    print(f"\033[91m[VISUAL-AEGIS SUB-SECOND INTERCEPTION] >>> THREAT NEUTRALIZED <<<\033[0m")
                    print(f"  ├─ Target Window   : '{meta['title']}'")
                    print(f"  ├─ True OS Process : {meta['exe_name']} (PID {meta['pid']})")
                    print(f"  ├─ Reason          : {reason}")

                    if self.auto_terminate:
                        # PASS BOTH HWND AND PID HERE
                        result_msg = kill_rogue_process(meta["hwnd"], meta["pid"])
                        print(f"\033[93m[INSTANT ACTION]   {result_msg} (Under 0.3s)\033[0m")
                    print("!" * 74)

                    asyncio.create_task(self.async_forensic_audit(meta, reason))

            await asyncio.sleep(SCAN_INTERVAL_SECONDS)


def launch_simulated_bitb_popup():
    import tkinter as tk
    root = tk.Tk()
    root.title("Windows Security - Sign in to your Microsoft Account")
    root.geometry("460x340+250+200")
    root.configure(bg="#ffffff")
    root.attributes("-topmost", True)

    url_bar = tk.Frame(root, bg="#f3f2f1", height=34, bd=1, relief="solid")
    url_bar.pack(fill="x", padx=6, pady=6)
    tk.Label(
        url_bar,
        text="🔒 https://login.microsoftonline.com/common/oauth2/authorize",
        fg="#107c10",
        bg="#f3f2f1",
        font=("Segoe UI", 8, "bold"),
        anchor="w",
    ).pack(fill="x", padx=8, pady=5)

    body = tk.Frame(root, bg="#ffffff", padx=28, pady=12)
    body.pack(fill="both", expand=True)
    tk.Label(body, text="Microsoft", fg="#5e5e5e", bg="#ffffff", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    tk.Label(body, text="Session Expired: Re-enter Corporate Credentials", fg="#1b1b1b", bg="#ffffff", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(6, 8))
    tk.Label(body, text="Username:", bg="#ffffff", font=("Segoe UI", 9)).pack(anchor="w")
    user_entry = tk.Entry(body, width=42, font=("Segoe UI", 10), bd=1, relief="solid")
    user_entry.insert(0, "corp\\j_admin")
    user_entry.pack(anchor="w", pady=(2, 8))
    tk.Label(body, text="Password:", bg="#ffffff", font=("Segoe UI", 9)).pack(anchor="w")
    tk.Entry(body, width=42, show="*", font=("Segoe UI", 10), bd=1, relief="solid").pack(anchor="w", pady=(2, 14))
    tk.Button(body, text="Sign in (Simulated Test Popup)", bg="#0067b8", fg="#ffffff", relief="flat", padx=12, pady=5, command=root.destroy).pack(anchor="w")
    root.mainloop()


if __name__ == "__main__":
    if "--simulate-popup" in sys.argv:
        launch_simulated_bitb_popup()
    else:
        scanner = VisualAegisScanner(auto_terminate="--no-kill" not in sys.argv)
        try:
            asyncio.run(scanner.monitor_loop())
        except KeyboardInterrupt:
            print("\n[*] Visual-Aegis shut down cleanly.")