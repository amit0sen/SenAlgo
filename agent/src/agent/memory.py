"""SenAlgo Agent Memory — persistent memory across sessions."""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
MEMORY_PATH = Path.home() / ".senalgo" / "memory.jsonl"
MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)


class AgentMemory:
    """Key-value persistent memory for the trading agent."""

    def __init__(self, path: Path = MEMORY_PATH):
        self.path = path
        self._cache: Dict[str, str] = {}
        self._load()

    def add(self, key: str, value: str) -> None:
        self._cache[key.strip().lower()] = value
        self._save()

    def get(self, key: str) -> Optional[str]:
        return self._cache.get(key.strip().lower())

    def search(self, query: str) -> List[Dict]:
        q = query.lower()
        return [{"key": k, "value": v} for k, v in self._cache.items() if q in k or q in v.lower()]

    def forget(self, key: str) -> bool:
        removed = self._cache.pop(key.strip().lower(), None)
        if removed:
            self._save()
        return removed is not None

    def list_all(self) -> List[Dict]:
        return [{"key": k, "value": v} for k, v in self._cache.items()]

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text().splitlines():
            try:
                entry = json.loads(line)
                self._cache[entry["key"]] = entry["value"]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.path, "w") as f:
            for k, v in self._cache.items():
                f.write(json.dumps({"key": k, "value": v}) + "\n")
