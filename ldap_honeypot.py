import asyncio
import datetime
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TELEMETRY_LOG = BASE_DIR / "mirage_telemetry.jsonl"
LDAP_PORT = 1389  # Non-admin port so it runs without root/admin rights


class LDAPDeceptionServer:
    def __init__(self):
        print("=" * 72)
        print("[*] MIRAGE-WARD: ACTIVE DIRECTORY LDAP HONEY-SCHEMA INITIALIZED")
        print(f"[*] Listening on port {LDAP_PORT} for attacker recon / BloodHound queries...")
        print("=" * 72)

    async def handle_ldap_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        print(f"\n[LDAP-TRAP] Inbound reconnaissance connection from {peer}")

        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break

                # Inspect raw query bytes for LDAP search requests
                query_str = data.decode("utf-8", errors="ignore")
                print(f"[LDAP RECON QUERY] {peer} -> Bytes received: {len(data)}")

                # Log telemetry event for Dashboard & Vaccine Forge
                event = {
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "source": str(peer),
                    "command": f"[LDAP-RECON] Attacker queried Active Directory schema structure from {peer}",
                    "canary_tripped": True,
                    "response_sample": "Returned 2 deceptive honey-admin accounts (backup_admin, dcsync_admin)",
                }
                with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")

                # Send back a convincing fake LDAP search response containing canary objects
                # (Simulating LDAP Bind Success + Deceptive Domain Admin Object entries)
                fake_ldap_response = (
                    b"\x30\x0c\x02\x01\x01\x61\x07\x0a\x01\x00\x04\x00\x04\x00"
                    b"CN=backup_admin,OU=Domain Controllers,DC=corp,DC=local\n"
                    b"CN=dcsync_admin,OU=Users,DC=corp,DC=local"
                )
                writer.write(fake_ldap_response)
                await writer.drain()
                break
        except Exception as e:
            print(f"[!] LDAP session error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"[LDAP-TRAP] Closed recon session with {peer}")


async def main():
    server = LDAPDeceptionServer()
    s = await asyncio.start_server(server.handle_ldap_client, "127.0.0.1", LDAP_PORT)
    async with s:
        await s.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] LDAP Honey-Schema stopped.")