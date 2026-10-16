import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).parent
SERVICES = (
    ("vulnerable MCP", "server_vulnerable.py", 9100),
    ("fixed MCP", "server_fixed.py", 9200),
    ("web UI", "web_app.py", 9300),
)


def main() -> None:
    processes: list[subprocess.Popen] = []
    try:
        for name, script, port in SERVICES:
            process = subprocess.Popen([sys.executable, script], cwd=BASE_DIR)
            processes.append(process)
            print(f"Started {name} on port {port} (pid {process.pid})", flush=True)

        print("\nOpen http://127.0.0.1:9300", flush=True)
        print("Keycloak and Ollama must already be running. Press Ctrl+C to stop.\n", flush=True)

        while all(process.poll() is None for process in processes):
            time.sleep(0.5)

        failed = next(process for process in processes if process.poll() is not None)
        raise SystemExit(f"A demo process exited unexpectedly with code {failed.returncode}.")
    except KeyboardInterrupt:
        print("\nStopping Scenario 5…", flush=True)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
