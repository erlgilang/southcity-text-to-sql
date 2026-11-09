import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Built with chr() because ruff format rewrites a unicode escape into the literal character
EM_DASH = chr(0x2014).encode()
SKIPPED_DIRS = {".git", ".venv", ".ruff_cache", ".pytest_cache", "__pycache__"}


def find_em_dashes(root: Path) -> list[str]:
    offenders = []
    for folder, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIPPED_DIRS]
        for name in filenames:
            # .env files hold secrets and are not part of the repo, uv.lock is generated
            if name.startswith(".env") or name == "uv.lock":
                continue
            path = Path(folder) / name
            if EM_DASH in path.read_bytes():
                offenders.append(str(path.relative_to(root)))
    return sorted(offenders)


def test_repo_has_no_em_dash():
    offenders = find_em_dashes(ROOT)
    assert not offenders, f"Em dash found in: {', '.join(offenders)}. Use a comma or colon."


def test_detector_finds_em_dash(tmp_path):
    (tmp_path / "bad.md").write_text(f"one {EM_DASH.decode()} two", encoding="utf-8")
    (tmp_path / "good.md").write_text("one, two", encoding="utf-8")
    assert find_em_dashes(tmp_path) == ["bad.md"]
