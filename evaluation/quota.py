"""Per-run request / token / retry accounting with optional caps (plan section 19: runs/quota.json, stop cleanly)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class QuotaExceeded(Exception):
    pass


class QuotaTracker:
    def __init__(self, path: Path | None = None, *, max_requests: int | None = None, max_total_tokens: int | None = None):
        self.path, self.max_requests, self.max_total_tokens = path, max_requests, max_total_tokens
        self.state: dict[str, Any] = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                                      "retries": 0, "provider_errors": 0, "by_provider": {}, "updated_at": None}
        if path is not None and path.exists():
            self.state.update(json.loads(path.read_text(encoding="utf-8")))

    def record_request(self, provider: str, usage: dict[str, int] | None) -> None:
        usage = usage or {}
        bp = self.state["by_provider"].setdefault(provider, {"requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        for d in (self.state, bp):
            d["requests"] += 1
            for k in ("input_tokens", "output_tokens", "total_tokens"):
                d[k] += int(usage.get(k, 0) or 0)

    def record_retry(self) -> None:
        self.state["retries"] += 1

    def record_provider_error(self) -> None:
        self.state["provider_errors"] += 1

    def check(self) -> None:
        """Raise QuotaExceeded if a cap is reached (called BEFORE starting an item, so items are never cut in half)."""
        if self.max_requests is not None and self.state["requests"] >= self.max_requests:
            raise QuotaExceeded(f"request cap reached ({self.state['requests']}/{self.max_requests}); resume later with --resume")
        if self.max_total_tokens is not None and self.state["total_tokens"] >= self.max_total_tokens:
            raise QuotaExceeded(f"token cap reached ({self.state['total_tokens']}/{self.max_total_tokens}); resume later with --resume")

    def save(self) -> None:
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.path is not None:
            self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
