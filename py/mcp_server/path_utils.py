from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """Find the repository root by walking upward until both py/ and skills/ exist."""
    resolved = start.resolve()
    for candidate in [resolved, *resolved.parents]:
        if (candidate / "py").exists() and (candidate / "skills").exists():
            return candidate
    raise RuntimeError(f"Unable to locate repository root from {resolved}")
