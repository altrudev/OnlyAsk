from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    timestamp: str
    transition_id: str
    event: str
    data: dict[str, Any]
    previous_hash: str
    entry_hash: str


class EvidenceLedger:
    """Append-only process ledger with deterministic hash chaining."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def append(self, transition_id: str, event: str, data: dict[str, Any]) -> LedgerEntry:
        previous_hash = self._entries[-1].entry_hash if self._entries else "0" * 64
        payload = {
            "sequence": len(self._entries),
            "transition_id": transition_id,
            "event": event,
            "data": data,
            "previous_hash": previous_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        entry = LedgerEntry(
            sequence=len(self._entries),
            timestamp=datetime.now(timezone.utc).isoformat(),
            transition_id=transition_id,
            event=event,
            data=data,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        previous = "0" * 64
        for entry in self._entries:
            payload = {
                "sequence": entry.sequence,
                "transition_id": entry.transition_id,
                "event": entry.event,
                "data": entry.data,
                "previous_hash": previous,
            }
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
            expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if entry.previous_hash != previous or entry.entry_hash != expected:
                return False
            previous = entry.entry_hash
        return True

    def export(self) -> list[dict[str, Any]]:
        return [asdict(entry) for entry in self._entries]
