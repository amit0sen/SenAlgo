"""SenAlgo session state store."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SESSIONS_DIR = Path.home() / ".senalgo" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class Session:
    def __init__(self, session_id: Optional[str] = None):
        self.id = session_id or str(uuid.uuid4())[:8]
        self.created_at = datetime.now().isoformat()
        self.messages: List[Dict] = []
        self.path = SESSIONS_DIR / f"{self.id}.jsonl"

    def append(self, role: str, content: str) -> None:
        entry = {"role": role, "content": content, "ts": datetime.now().isoformat()}
        self.messages.append(entry)
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @classmethod
    def load(cls, session_id: str) -> "Session":
        s = cls(session_id)
        if s.path.exists():
            for line in s.path.read_text().splitlines():
                try:
                    s.messages.append(json.loads(line))
                except Exception:
                    pass
        return s

    @classmethod
    def list_all(cls) -> List[Dict]:
        sessions = []
        for p in sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
            sid = p.stem
            msgs = []
            try:
                for line in p.read_text().splitlines()[:2]:
                    msgs.append(json.loads(line))
            except Exception:
                pass
            sessions.append({"id": sid, "messages": len(msgs), "path": str(p)})
        return sessions
