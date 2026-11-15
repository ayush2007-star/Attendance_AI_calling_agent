import json
import subprocess
import sys
import time
from pathlib import Path


def _run_stop_script(repo_root: Path) -> subprocess.CompletedProcess:
    stop_script = repo_root / "scripts" / "stop-local.ps1"
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(stop_script)]
    return subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)


def test_stop_local_stops_project_owned_process():
    """
    Verify that stop-local.ps1 stops a process that belongs to the current
    project session and matches the recorded process identity.
    """
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / ".run"
    run_dir.mkdir(exist_ok=True)
    pids_file = run_dir / "pids.json"

    # Spawn a process with a distinct marker in its command line
    owned_proc = subprocess.Popen(
        [sys.executable, "-c", "import time\n# test_marker_backend\ntime.sleep(25)"]
    )
    owned_pid = owned_proc.pid

    try:
        pids_file.write_text(
            json.dumps(
                {
                    "backend": {
                        "pid": owned_pid,
                        "name": "backend",
                        "marker": "test_marker_backend",
                        "started_at": "2026-11-15T00:00:00Z",
                    }
                }
            )
        )

        result = _run_stop_script(repo_root)
        assert result.returncode == 0
        assert "stopped" in result.stdout.lower()

        # Allow time for termination
        time.sleep(1)
        assert owned_proc.poll() is not None, f"Project process {owned_pid} should have been stopped!"
        assert not pids_file.exists(), ".run/pids.json should have been cleaned up"

    finally:
        try:
            owned_proc.terminate()
            owned_proc.wait(timeout=2)
        except Exception:
            pass
        if pids_file.exists():
            pids_file.unlink()


def test_stop_local_does_not_terminate_unrelated_processes():
    """
    Verify that stop-local.ps1 checks .run/pids.json and never terminates
    an unrelated application or process running concurrently.
    """
    repo_root = Path(__file__).resolve().parents[2]

    # Spawn an independent, unrelated process
    unrelated_proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)"]
    )
    unrelated_pid = unrelated_proc.pid

    try:
        result = _run_stop_script(repo_root)
        assert result.returncode == 0

        # Verify the unrelated process is still alive and polling returns None
        poll_status = unrelated_proc.poll()
        assert poll_status is None, f"Unrelated process {unrelated_pid} was unexpectedly terminated!"

    finally:
        try:
            unrelated_proc.terminate()
            unrelated_proc.wait(timeout=2)
        except Exception:
            pass


def test_stop_local_does_not_kill_mismatched_or_reused_pids():
    """
    Verify safety shield: if a PID is alive but its command line does NOT match
    the expected project service marker, stop-local.ps1 skips it without killing it.
    """
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / ".run"
    run_dir.mkdir(exist_ok=True)
    pids_file = run_dir / "pids.json"

    # Spawn an independent process whose command line does NOT contain "start_backend.ps1"
    unrelated_proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)"]
    )
    unrelated_pid = unrelated_proc.pid

    try:
        # Record this PID claiming it is backend with marker "start_backend.ps1"
        pids_file.write_text(
            json.dumps(
                {
                    "backend": {
                        "pid": unrelated_pid,
                        "name": "backend",
                        "marker": "start_backend.ps1",
                        "started_at": "2026-11-15T00:00:00Z",
                    }
                }
            )
        )

        result = _run_stop_script(repo_root)
        assert result.returncode == 0
        assert "SAFETY SHIELD" in result.stdout

        # Verify the unrelated process was NOT killed
        assert unrelated_proc.poll() is None, f"Mismatched process {unrelated_pid} was killed!"

    finally:
        try:
            unrelated_proc.terminate()
            unrelated_proc.wait(timeout=2)
        except Exception:
            pass
        if pids_file.exists():
            pids_file.unlink()


def test_stop_local_handles_stale_process_records():
    """
    Verify that if .run/pids.json points to a nonexistent/dead PID,
    stop-local.ps1 safely handles it and cleans up the tracking file.
    """
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / ".run"
    run_dir.mkdir(exist_ok=True)
    pids_file = run_dir / "pids.json"

    try:
        pids_file.write_text(
            json.dumps(
                {
                    "stale_service": {
                        "pid": 999999,
                        "name": "stale_service",
                        "marker": "stale_marker",
                    }
                }
            )
        )

        result = _run_stop_script(repo_root)
        assert result.returncode == 0
        assert "already terminated" in result.stdout.lower()
        assert not pids_file.exists()

    finally:
        if pids_file.exists():
            pids_file.unlink()


def test_stop_local_repeated_runs_safe():
    """
    Verify that running stop-local.ps1 multiple times in a row when idle
    does not throw errors and exits cleanly with 0.
    """
    repo_root = Path(__file__).resolve().parents[2]
    pids_file = repo_root / ".run" / "pids.json"
    if pids_file.exists():
        pids_file.unlink()

    run1 = _run_stop_script(repo_root)
    assert run1.returncode == 0
    assert "No active project run session found" in run1.stdout

    run2 = _run_stop_script(repo_root)
    assert run2.returncode == 0
    assert "No active project run session found" in run2.stdout
