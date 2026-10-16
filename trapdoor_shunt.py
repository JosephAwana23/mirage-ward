import asyncio
import subprocess
import sys
import psutil

# Configuration
EXPOSED_C2_HOST = "127.0.0.1"
EXPOSED_C2_PORT = 4444
MIRAGE_HOST = "127.0.0.1"
MIRAGE_PORT = 9990
RISK_THRESHOLD = 0.65


def spawn_safe_dummy_beacon() -> subprocess.Popen:
    """Spawns a harmless sleeper subprocess to safely demonstrate PID suspension."""
    dummy_code = "import time\nwhile True:\n    time.sleep(1)\n"
    return subprocess.Popen(
        [sys.executable, "-c", dummy_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def freeze_process(pid: int) -> str:
    """Suspends the target OS process in memory without terminating its PID."""
    try:
        target = psutil.Process(pid)
        if target.status() != psutil.STATUS_STOPPED:
            target.suspend()
        return target.status()
    except psutil.NoSuchProcess:
        return "TERMINATED"
    except Exception as e:
        return f"ERROR ({e})"


async def pipe_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def intercept_and_shunt(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    suspect_pid: int,
):
    attacker_addr = client_writer.get_extra_info("peername")
    print("\n" + "=" * 68)
    print(f"[TRAPDOOR-SHUNT] Inbound connection on C2 Port {EXPOSED_C2_PORT} from {attacker_addr}")

    calculated_risk = 0.88
    print(f"[HEURISTIC GATE] Risk Score R = {calculated_risk} (Threshold >= {RISK_THRESHOLD}) -> ESCALATE")

    status = freeze_process(suspect_pid)
    print(
        f"\033[93m[PROCESS FREEZE] PID {suspect_pid} suspended in RAM! "
        f"Current OS Status: '{status}' (Real host protected)\033[0m"
    )

    try:
        mirage_reader, mirage_writer = await asyncio.open_connection(MIRAGE_HOST, MIRAGE_PORT)
        print(
            f"\033[92m[SOCKET SHUNT]   Diverted {attacker_addr} -> "
            f"Mirage Sandbox ({MIRAGE_HOST}:{MIRAGE_PORT})\033[0m"
        )
        print("=" * 68)

        await asyncio.gather(
            pipe_stream(client_reader, mirage_writer),
            pipe_stream(mirage_reader, client_writer),
        )
    except ConnectionRefusedError:
        msg = b"[!] Mirage-Weaver sandbox is not running on port 9990.\r\n"
        client_writer.write(msg)
        await client_writer.drain()
        client_writer.close()
        print("[!] Error: Could not shunt stream. Make sure mirage_weaver.py is running first!")


async def run_shunt_daemon():
    dummy_proc = spawn_safe_dummy_beacon()
    suspect_pid = dummy_proc.pid
    print(f"[*] Spawned safe test target process -> PID: {suspect_pid} (Status: {psutil.Process(suspect_pid).status()})")
    print(f"[*] Trapdoor Shunt monitoring {EXPOSED_C2_HOST}:{EXPOSED_C2_PORT}...")
    print(f"[*] Ready! Open another terminal and run: python trapdoor_shunt.py --attacker")

    server = await asyncio.start_server(
        lambda r, w: intercept_and_shunt(r, w, suspect_pid),
        EXPOSED_C2_HOST,
        EXPOSED_C2_PORT,
        reuse_address=True,
    )

    try:
        async with server:
            await server.serve_forever()
    finally:
        print(f"\n[*] Cleaning up suspended test process (PID {suspect_pid})...")
        try:
            p = psutil.Process(suspect_pid)
            p.resume()
            p.terminate()
            print("[*] Test process terminated cleanly.")
        except psutil.NoSuchProcess:
            pass


async def run_attacker_simulator():
    print(f"[*] Connecting to target host {EXPOSED_C2_HOST}:{EXPOSED_C2_PORT}...")
    try:
        reader, writer = await asyncio.open_connection(EXPOSED_C2_HOST, EXPOSED_C2_PORT)
    except ConnectionRefusedError:
        print("[!] Connection refused. Make sure trapdoor_shunt.py is running!")
        return

    async def read_from_server():
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    print("\n[*] Connection closed by remote host.")
                    break
                sys.stdout.write(data.decode("utf-8", errors="ignore"))
                sys.stdout.flush()
        except asyncio.CancelledError:
            pass

    recv_task = asyncio.create_task(read_from_server())

    try:
        while not recv_task.done():
            cmd = await asyncio.to_thread(sys.stdin.readline)
            if not cmd:
                break
            writer.write(cmd.encode("utf-8"))
            await writer.drain()
            if cmd.strip().lower() in ("exit", "quit"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        recv_task.cancel()
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    try:
        if "--attacker" in sys.argv:
            asyncio.run(run_attacker_simulator())
        else:
            asyncio.run(run_shunt_daemon())
    except KeyboardInterrupt:
        print("\n[*] Exiting.")
