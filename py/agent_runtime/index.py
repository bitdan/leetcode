import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set


CODE_EXTENSIONS = {
    ".py",
    ".java",
    ".ts",
    ".tsx",
    ".js",
    ".vue",
    ".md",
    ".xml",
    ".yml",
    ".yaml",
    ".json",
    ".sql",
    ".toml",
    ".ini",
    ".properties",
}

IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    ".pytest_cache",
}


@dataclass
class DocumentChunk:
    path: str
    start_line: int
    text: str
    tokens: Set[str]


class ProjectDocumentIndex:
    """Small local code index used by the project agent.

    This is intentionally dependency-free. It is not a replacement for vector
    search, but it gives deterministic retrieval and keeps tests fast.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.chunks: List[DocumentChunk] = []
        self.indexed_files = 0
        self.built_at = 0.0

    def build(self, max_files: int = 300, force: bool = False) -> Dict[str, int | bool]:
        if self.chunks and not force:
            return {"indexed_files": self.indexed_files, "chunks": len(self.chunks), "rebuilt": False}

        chunks: List[DocumentChunk] = []
        indexed_files = 0
        for path in self._iter_indexable_files():
            if indexed_files >= max_files:
                break
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not text.strip():
                continue
            indexed_files += 1
            chunks.extend(self._chunk_file(path, text))

        self.chunks = chunks
        self.indexed_files = indexed_files
        self.built_at = time.time()
        return {"indexed_files": indexed_files, "chunks": len(chunks), "rebuilt": True}

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, object]]:
        if not self.chunks:
            self.build()
        query_tokens = self._tokens(query)
        if not query_tokens:
            return []

        scored = []
        lowered_query = query.lower()
        for chunk in self.chunks:
            overlap = query_tokens.intersection(chunk.tokens)
            phrase_bonus = 2 if lowered_query and lowered_query in chunk.text.lower() else 0
            score = len(overlap) + phrase_bonus
            if score <= 0:
                continue
            scored.append((score, chunk))

        scored.sort(key=lambda item: (-item[0], item[1].path, item[1].start_line))
        return [
            {
                "path": chunk.path,
                "line": chunk.start_line,
                "score": score,
                "snippet": self._snippet(chunk.text),
            }
            for score, chunk in scored[:max_results]
        ]

    def _iter_indexable_files(self):
        for path in self.project_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in CODE_EXTENSIONS:
                continue
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            yield path

    def _chunk_file(self, path: Path, text: str) -> List[DocumentChunk]:
        lines = text.splitlines()
        chunks = []
        chunk_size = 40
        step = 30
        for start in range(0, len(lines), step):
            window = lines[start:start + chunk_size]
            if not window:
                break
            chunk_text = "\n".join(window).strip()
            if not chunk_text:
                continue
            chunks.append(
                DocumentChunk(
                    path=self._relative(path),
                    start_line=start + 1,
                    text=chunk_text[:4000],
                    tokens=self._tokens(chunk_text),
                )
            )
        return chunks

    def _tokens(self, text: str) -> Set[str]:
        english = re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}", text.lower())
        cjk = re.findall(r"[\u4e00-\u9fa5]{2,}", text)
        tokens = set(english)
        for item in cjk:
            tokens.add(item)
            for index in range(0, max(len(item) - 1, 0)):
                tokens.add(item[index:index + 2])
        return tokens

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.project_root)).replace("\\", "/")

    def _snippet(self, text: str) -> str:
        value = " ".join(line.strip() for line in text.splitlines() if line.strip())
        return value[:320]
