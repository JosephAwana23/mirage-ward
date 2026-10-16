import ast
import asyncio
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from google import genai
from google.genai import types


def load_local_env():
    """Automatically loads key=value pairs from .env in the same folder."""
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


load_local_env()

try:
    import yara
    YARA_AVAILABLE = True
except ImportError:
    YARA_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
TELEMETRY_LOG = str(BASE_DIR / "mirage_telemetry.jsonl")
VACCINE_DIR = str(BASE_DIR / "generated_vaccines")
MANIFEST_FILE = os.path.join(VACCINE_DIR, "immunity_manifest.json")
MODEL_ID = "gemini-3.8-flash"

HIGH_RISK_PATTERNS = [
    "Invoke-WebRequest",
    "certutil",
    "bitsadmin",
    "mimikatz",
    "reg save",
    "vssadmin",
    "net user",
    "whoami /priv",
    "[VISUAL-SPOOF]",
]

YARA_SYSTEM_PROMPT = """You are an elite Blue Team YARA signature engineer.
Given an attacker's shell command captured inside a deception honeypot, output ONLY a valid, standalone YARA rule.
Do NOT wrap the rule in markdown code fences. Include `meta:`, `strings:`, and `condition:` sections.
"""


class VaccineForge:
    def __init__(self, enforce_firewall: bool = False):
        os.makedirs(VACCINE_DIR, exist_ok=True)
        self.enforce_firewall = enforce_firewall
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.processed_signatures: set[str] = set()

        print("=" * 72)
        print("[*] MIRAGE-WARD: AUTO-VACCINE FORGE INITIALIZED")
        print(f"[*] AI Synthesis Engine : {MODEL_ID if self.client else 'Deterministic Local Compiler (No API Key)'}")
        print(f"[*] Output Directory    : {VACCINE_DIR}")
        print("=" * 72)

    def extract_ip(self, peer_str: str) -> str:
        try:
            parsed = ast.literal_eval(peer_str)
            if isinstance(parsed, tuple) and len(parsed) >= 1:
                return str(parsed[0])
        except Exception:
            pass
        match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", peer_str)
        return match.group(1) if match else "127.0.0.1"

    def build_fallback_yara(self, rule_name: str, command: str, source_ip: str, timestamp: str) -> str:
        escaped_cmd = command.replace("\\", "\\\\").replace('"', '\\"')
        return f"""rule {rule_name} {{
    meta:
        author = "Mirage-Ward Auto-Vaccine Forge"
        description = "Auto-synthesized signature from shunted C2 session"
        attacker_ip = "{source_ip}"
        captured_at = "{timestamp}"
        severity = "CRITICAL"
        mitre_attack = "T1552.001"

    strings:
        $cmd_exact = "{escaped_cmd}" nocase ascii wide
        $canary_aws = "AKIAIOSFODNN7CANARY99" ascii wide
        $canary_pwd = "P@ssw0rd_Canary_2026!" ascii wide

    condition:
        $cmd_exact or any of ($canary_*)
}}"""

    async def synthesize_yara_rule(self, rule_name: str, command: str, source_ip: str, timestamp: str) -> str:
        yara_text = ""
        if self.client:
            try:
                prompt = (
                    f"Rule Name: {rule_name}\nAttacker IP: {source_ip}\n"
                    f"Captured Command: {command}\nTimestamp: {timestamp}"
                )
                resp = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=MODEL_ID,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=YARA_SYSTEM_PROMPT,
                        temperature=0.1,
                    ),
                )
                if resp and resp.text:
                    cleaned = re.sub(r"^```(?:yara)?\s*|\s*```$", "", resp.text.strip(), flags=re.MULTILINE)
                    if "rule " in cleaned and "strings:" in cleaned and "condition:" in cleaned:
                        yara_text = cleaned
            except Exception as e:
                print(f"[!] Gemini YARA Notice ({e}). Using deterministic rule compiler.")

        if not yara_text:
            yara_text = self.build_fallback_yara(rule_name, command, source_ip, timestamp)

        if YARA_AVAILABLE:
            try:
                yara.compile(source=yara_text)
            except Exception:
                yara_text = self.build_fallback_yara(rule_name, command, source_ip, timestamp)

        return yara_text

    def stage_firewall_rule(self, source_ip: str, incident_id: str) -> dict:
        rule_name = f"MirageWard_Block_{incident_id}"
        netsh_cmd = (
            f'netsh advfirewall firewall add rule name="{rule_name}" '
            f"dir=in action=block remoteip={source_ip}"
        )
        if source_ip in ("127.0.0.1", "::1", "localhost"):
            status = "DRY_RUN_LOOPBACK_PROTECTED"
            note = "Target is localhost (127.0.0.1). Rule staged for SIEM broadcast without blocking local loopback."
        else:
            status = "STAGED_DRY_RUN"
            note = "External IP rule staged."
        return {
            "rule_name": rule_name,
            "target_ip": source_ip,
            "command": netsh_cmd,
            "enforcement_status": status,
            "note": note,
        }

    async def process_event(self, event: dict):
        cmd = event.get("command", "").strip()
        canary_tripped = bool(event.get("canary_tripped", False))
        peer = event.get("source", "('127.0.0.1', 0)")
        timestamp = event.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat())

        is_high_risk = any(pat.lower() in cmd.lower() for pat in HIGH_RISK_PATTERNS)
        if not canary_tripped and not is_high_risk:
            return

        source_ip = self.extract_ip(peer)
        dedup_key = f"{source_ip}:{cmd.lower()}"
        if dedup_key in self.processed_signatures:
            return
        self.processed_signatures.add(dedup_key)

        short_hash = hashlib.sha256(f"{timestamp}:{cmd}".encode("utf-8")).hexdigest()[:8]
        rule_name = f"Mirage_AutoVaccine_{short_hash}"

        print("\n" + "!" * 72)
        trigger_type = "CANARY HONEY-TOKEN TRIPWIRE" if canary_tripped else "HIGH-RISK RECON COMMAND"
        print(f"\033[91m[VACCINE-FORGE] >>> TRIGGER: {trigger_type} DETECTED <<<\033[0m")
        print(f"  ├─ Source Peer : {peer}")
        print(f"  └─ Attacker Cmd: {cmd}")

        yara_rule = await self.synthesize_yara_rule(rule_name, cmd, source_ip, timestamp)
        yara_filename = f"{rule_name}.yar"
        yara_path = os.path.join(VACCINE_DIR, yara_filename)
        with open(yara_path, "w", encoding="utf-8") as f:
            f.write(yara_rule + "\n")

        print(f"\033[92m[+] Compiled YARA Vaccine  : {yara_path}\033[0m")

        fw_action = self.stage_firewall_rule(source_ip, short_hash)
        print(f"\033[93m[+] Firewall Action [{fw_action['enforcement_status']}]: {fw_action['command']}\033[0m")

        manifest_payload = {
            "incident_id": f"MW-{short_hash.upper()}",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "trigger_reason": trigger_type,
            "attacker_command": cmd,
            "yara_file": yara_filename,
            "yara_rule_sha256": hashlib.sha256(yara_rule.encode("utf-8")).hexdigest(),
            "firewall_mitigation": fw_action,
        }
        payload_bytes = json.dumps(manifest_payload, sort_keys=True).encode("utf-8")
        manifest_payload["manifest_signature_sha256"] = hashlib.sha256(payload_bytes).hexdigest()

        existing = []
        if os.path.exists(MANIFEST_FILE):
            try:
                with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.append(manifest_payload)

        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        print(f"\033[96m[+] Signed Immunity Manifest: {MANIFEST_FILE}\033[0m")
        print("!" * 72)


async def tail_telemetry(forge: VaccineForge):
    if not os.path.exists(TELEMETRY_LOG):
        open(TELEMETRY_LOG, "a", encoding="utf-8").close()
    print(f"[*] Watching {TELEMETRY_LOG} for live deception tripwires...")
    
    while True:
        try:
            with open(TELEMETRY_LOG, "r", encoding="utf-8") as f:
                # Seek to end to catch new events, or read all if small
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line:
                        await asyncio.sleep(0.5)
                        continue
                    try:
                        event = json.loads(line.strip())
                        await forge.process_event(event)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"[!] Telemetry read notice ({e}). Re-connecting stream in 2s...")
            await asyncio.sleep(2.0)


if __name__ == "__main__":
    forge = VaccineForge(enforce_firewall="--enforce-firewall" in sys.argv)
    try:
        asyncio.run(tail_telemetry(forge))
    except KeyboardInterrupt:
        print("\n[*] Auto-Vaccine Forge stopped cleanly.")
