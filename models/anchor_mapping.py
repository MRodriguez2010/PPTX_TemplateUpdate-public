from __future__ import annotations

from dataclasses import dataclass, field

from models.anchor_record import AnchorRecord


@dataclass
class AnchorMapping:
    anchor_key: str
    existing_anchor: AnchorRecord | None = None
    new_anchor: AnchorRecord | None = None
    include_in_test: bool = True
    test_value: str = ""
    notes: list[str] = field(default_factory=list)
