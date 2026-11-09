"""Journal JSONL d'exécution pour auditer les sources et résultats du scénario."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_audit_log(
    audit_id: str,
    scenario_id: str,
    started_at: str,
    completed_at: str,
    events: list[dict[str, Any]],
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as output:
        header = {
            "record_type": "audit_started",
            "audit_id": audit_id,
            "scenario_id": scenario_id,
            "started_at": started_at,
        }
        output.write(json.dumps(header, ensure_ascii=False) + "\n")
        for event in events:
            output.write(
                json.dumps(
                    {"record_type": "event_assessed", "audit_id": audit_id, **event},
                    ensure_ascii=False,
                )
                + "\n"
            )
        footer = {
            "record_type": "audit_completed",
            "audit_id": audit_id,
            "completed_at": completed_at,
            "events_processed": len(events),
        }
        output.write(json.dumps(footer, ensure_ascii=False) + "\n")