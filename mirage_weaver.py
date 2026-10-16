import asyncio
import datetime
import json
import os
from pathlib import Path
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

# Configuration
MIRAGE_HOST = "127.0.0.1"
MIRAGE_PORT = 9990
MODEL_ID = "gemini-3.8-flash"
TELEMETRY_LOG = str(Path(__file__).resolve().parent / "mirage_telemetry.jsonl")

# Seeded Honey-Tokens & Virtual Filesystem State
CANARY_FILES = {
    "aws_prod_keys.env": (
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7CANARY99\n"
        "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYCANARYKEY\n"
        "AWS_DEFAULT_REGION=us-west-2\n"
        "# INTERNAL NOTE: Prod Vault SSH Jumpbox -> 10.240.12.88:22"
    ),
    "network_passwords.txt": (
        "Domain Admin Backup: P@ssw0rd_Canary_2026!\n"
        "SIEM Collector Token: gha_live_99812347109283471092"
    ),
}

SYSTEM_PROMPT = """You are Mirage-Ward, a high-interaction Windows 11 Enterprise Command Prompt (cmd.exe) deception environment.
The attacker believes they have compromised 'CORP-WKSTN-04' as user 'corp\\j_admin' in directory 'C:\\Users\\j_admin\\Desktop\\Ops_Vault'.

Virtual Directory Contents:
- aws_prod_keys.env (842 bytes)
- network_passwords.txt (412 bytes)
- deploy_agent.ps1 (2,140 bytes)
- Quarter4_Financials.xlsx (48,920 bytes)

Rules:
1. Respond ONLY with the raw text output that Windows cmd.exe or PowerShell would print for the given command.
2. Do NOT wrap output in markdown code blocks or add explanations.
3. Keep directory contents, IP addresses (10.240.12.15), and process lists consistent.
"""


class MirageEngine:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.cwd = r"C:\Users\j_admin\Desktop\Ops_Vault"
        if self.client:
            masked = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "Loaded"
            print(f"[+] Loaded GEMINI_API_KEY from .env ({masked}) -> Engine: {MODEL_ID}")
        else:
            print("[!] GEMINI_API_KEY not found in .env. Running in Local Fallback Deception Mode.")

    def log_telemetry(self, peer: str, command: str, canary_tripped: bool, response_preview: str):
        event = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": peer,
            "command": command,
            "canary_tripped": canary_tripped,
            "response_sample": response_preview[:120],
        }
        with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    async def evaluate_command(self, cmd: str, history: list[str]) -> tuple[str, bool]:
        cmd_lower = cmd.lower().strip()
        canary_tripped = False

        # 1. Check Deterministic Canary Honey-Token Tripwires
        for filename, content in CANARY_FILES.items():
            if filename.lower() in cmd_lower and any(
                verb in cmd_lower for verb in ["type", "cat", "get-content", "more", "findstr"]
            ):
                canary_tripped = True
                return content, canary_tripped

        # 2. If Gemini API is configured, synthesize cognitive shell response
        if self.client:
            try:
                context_str = "\n".join(history[-6:])
                prompt = (
                    f"Recent Session History:\n{context_str}\n\n"
                    f"Current Directory: {self.cwd}\n"
                    f"Attacker Command: {cmd}"
                )
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=MODEL_ID,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    return response.text.strip(), canary_tripped
            except Exception as e:
                print(f"[!] Gemini API Notice ({e}). Using local fallback for '{cmd}'.")

        # 3. Built-in Offline Fallback Emulator
        if cmd_lower in ("whoami", "whoami /all", "whoami /priv"):
            return "corp\\j_admin\r\nPrivilege: SeDebugPrivilege [Enabled]", canary_tripped
        elif cmd_lower.startswith("dir") or cmd_lower == "ls":
            return (
                f" Volume in drive C is OSDisk\r\n Directory of {self.cwd}\r\n\r\n"
                "10/15/2026  08:14 PM    <DIR>          .\r\n"
                "10/15/2026  08:14 PM    <DIR>          ..\r\n"
                "10/14/2026  11:20 AM               842 aws_prod_keys.env\r\n"
                "10/12/2026  04:05 PM               412 network_passwords.txt\r\n"
                "10/10/2026  09:15 AM             2,140 deploy_agent.ps1\r\n"
                "10/09/2026  02:44 PM            48,920 Quarter4_Financials.xlsx\r\n"
                "               4 File(s)         52,314 bytes"
            ), canary_tripped
        elif cmd_lower.startswith("ipconfig"):
            return (
                "Windows IP Configuration\r\n\r\n"
                "Ethernet adapter CorpLAN:\r\n"
                "   IPv4 Address. . . . . . . . . . . : 10.240.12.15\r\n"
                "   Subnet Mask . . . . . . . . . . . : 255.255.255.0\r\n"
                "   Default Gateway . . . . . . . . . : 10.240.12.1"
            ), canary_tripped
        elif cmd_lower in ("hostname",):
            return "CORP-WKSTN-04", canary_tripped
        else:
            return f"'{cmd.split()[0]}' executed in sandbox context (0 errors).", canary_tripped


async def handle_shunted_session(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, engine: MirageEngine
):
    peer = str(writer.get_extra_info("peername"))
    print(f"\n[MIRAGE-WEAVER] >>> Shunted C2 stream received from {peer}")

    history: list[str] = []
    banner = (
        "Microsoft Windows [Version 10.0.26100.1]\r\n"
        "(c) Microsoft Corporation. All rights reserved.\r\n\r\n"
    )
    writer.write(banner.encode("utf-8"))
    await writer.drain()

    try:
        while True:
            prompt = f"\r\n{engine.cwd}> "
            writer.write(prompt.encode("utf-8"))
            await writer.drain()

            line = await reader.readline()
            if not line:
                break

            cmd = line.decode("utf-8", errors="ignore").strip()
            if not cmd:
                continue

            if cmd.lower() in ("exit", "quit"):
                writer.write(b"Session terminated.\r\n")
                await writer.drain()
                break

            print(f"[ATTACKER CMD] {peer} -> {cmd}")
            output, canary_tripped = await engine.evaluate_command(cmd, history)

            if canary_tripped:
                print(
                    f"\033[91m[!!! CANARY HONEY-TOKEN TRIPPED !!!] "
                    f"Attacker exfiltrated bait file via: '{cmd}'\033[0m"
                )

            history.append(f"{engine.cwd}> {cmd}\n{output}")
            engine.log_telemetry(peer, cmd, canary_tripped, output)

            formatted_output = output.replace("\r\n", "\n").replace("\n", "\r\n") + "\r\n"
            writer.write(formatted_output.encode("utf-8"))
            await writer.drain()

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[!] Session error with {peer}: {e}")
    finally:
        print(f"[MIRAGE-WEAVER] <<< Closed deception session for {peer}")
        writer.close()
        await writer.wait_closed()


async def main():
    engine = MirageEngine()
    server = await asyncio.start_server(
        lambda r, w: handle_shunted_session(r, w, engine), MIRAGE_HOST, MIRAGE_PORT, reuse_address=True
    )
    print(f"[*] Mirage-Weaver Deception Sandbox listening on {MIRAGE_HOST}:{MIRAGE_PORT}")
    print(f"[*] Forensic telemetry logging to: {TELEMETRY_LOG}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Mirage-Weaver shut down cleanly.")
