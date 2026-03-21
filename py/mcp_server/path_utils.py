from pathlib import Path


def find_repo_root(start: Path) -> Path:
    resolved = start.resolve()
    for candidate in [resolved, *resolved.parents]:
        if (candidate / "py").exists() and (candidate / "skills").exists():
            return candidate
    raise RuntimeError(f"Unable to locate repository root from {resolved}")
