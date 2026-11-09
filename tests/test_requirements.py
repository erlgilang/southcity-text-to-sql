import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
def test_requirements_txt_matches_the_lock_file():
    exported = subprocess.run(
        ["uv", "export", "--no-dev", "--no-hashes", "--frozen"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    committed = (ROOT / "requirements.txt").read_text()
    # The header line records the output path, so compare only the pinned lines.
    assert pinned(exported) == pinned(committed), (
        "Run: uv export --no-dev --no-hashes -o requirements.txt"
    )


def pinned(text: str) -> list[str]:
    return [line for line in text.splitlines() if "==" in line and not line.startswith("#")]
