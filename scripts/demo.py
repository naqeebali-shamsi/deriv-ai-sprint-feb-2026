#!/usr/bin/env python3
"""Cross-platform demo runner (works on Windows + Linux + macOS).

Starts all services, seeds data, and shows the full autonomy loop.
Usage: python scripts/demo.py
"""
import atexit
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# Track subprocesses for cleanup
processes: list[subprocess.Popen] = []


def cleanup():
    """Kill all spawned subprocesses."""
    print("\nShutting down services...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    print("All services stopped.")


atexit.register(cleanup)


def run_bg(cmd: list[str], label: str) -> subprocess.Popen:
    """Start a background process."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    processes.append(proc)
    print(f"  Started {label} (PID {proc.pid})")
    return proc


def run_fg(cmd: list[str], label: str, timeout: int = 60) -> bool:
    """Run a foreground command and wait for completion."""
    result = subprocess.run(
        cmd,
        capture_output=False,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=timeout,
    )
    return result.returncode == 0


def wait_for_backend(url: str = "http://localhost:8000/health", retries: int = 15):
    """Wait for the backend to become healthy."""
    import httpx
    for i in range(retries):
        try:
            resp = httpx.get(url, timeout=2)
            if resp.status_code == 200:
                print("  Backend is healthy!")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("  WARNING: Backend may not be ready")
    return False


def main():
    print("=" * 50)
    print("  Autonomous Fraud Agent - Demo Runner")
    print("  Deriv AI Talent Sprint 2026")
    print("=" * 50)

    py = sys.executable  # Use same Python interpreter

    # Step 1: Init DB
    print("\n[1/6] Initializing database...")
    db_path = PROJECT_ROOT / "app.db"
    if db_path.exists():
        db_path.unlink()
    run_fg([py, "scripts/init_db.py"], "init_db")

    # Step 2: Validate schemas
    print("\n[2/7] Validating schemas...")
    if not run_fg([py, "scripts/validate_schemas.py"], "validate_schemas"):
        print("ERROR: Schema validation failed!")
        sys.exit(1)

    # Step 3: Bootstrap model (required for scoring)
    print("\n[3/7] Bootstrapping ML model...")
    if not run_fg([py, "scripts/bootstrap_model.py", "--force"], "bootstrap_model"):
        print("ERROR: Model bootstrap failed!")
        sys.exit(1)

    # Step 4: Start backend
    print("\n[4/7] Starting backend (FastAPI)...")
    backend = run_bg(
        [py, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        "backend",
    )
    time.sleep(2)
    wait_for_backend()

    # Step 5: Seed demo data
    print("\n[5/7] Seeding demo data...")
    run_fg([py, "scripts/seed_demo.py", "--count", "200"], "seed_demo", timeout=300)

    # Step 6: Start Streamlit UI
    print("\n[6/7] Starting UI (Streamlit)...")
    run_bg(
        [py, "-m", "streamlit", "run", "ui/app.py",
         "--server.port", "8501", "--server.headless", "true"],
        "streamlit",
    )
    time.sleep(2)

    # Step 7: Start simulator
    print("\n[7/7] Starting live transaction simulator (1 TPS)...")
    run_bg(
        [py, "-m", "sim.main", "--tps", "1"],
        "simulator",
    )

    print("\n" + "=" * 50)
    print("  Demo is running!")
    print("=" * 50)
    print()
    print("URLs:")
    print("  Backend API:  http://localhost:8000")
    print("  API Docs:     http://localhost:8000/docs")
    print("  Streamlit UI: http://localhost:8501")
    print()
    print("What judges will see:")
    print("  1. Transaction stream flowing in real-time")
    print("  2. Risk scores computed by ML model")
    print("  3. Cases opening automatically for high-risk txns")
    print("  4. Analyst can label cases (fraud/legit)")
    print("  5. Model retrains with new labels")
    print("  6. Pattern cards from graph mining (rings, hubs)")
    print()
    print("Press Ctrl+C to stop all services.")
    print("=" * 50)

    # Wait until interrupted
    try:
        while True:
            # Check if backend is still alive
            if backend.poll() is not None:
                print("WARNING: Backend process died!")
                break
            time.sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
