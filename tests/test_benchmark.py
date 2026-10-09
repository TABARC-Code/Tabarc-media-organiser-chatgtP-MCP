import json
import subprocess
import sys
from pathlib import Path


def test_synthetic_benchmark_reports_repeat_scan(tmp_path):
    script = Path(__file__).resolve().parents[1] / "tools" / "benchmark_scanner.py"
    result = subprocess.run(
        [sys.executable, str(script), "--files", "12", "--profile", "quiet"],
        check=True, capture_output=True, text=True, timeout=20,
        cwd=tmp_path,
    )
    data = json.loads(result.stdout)
    assert data["file_count"] == 12
    assert data["initial_scan"]["new_or_changed"] == 12
    assert data["repeat_scan"]["new_or_changed"] == 0
    assert data["repeat_scan"]["errors"] == 0
