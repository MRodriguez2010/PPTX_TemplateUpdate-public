"""Auto-match anchors between existing and new templates by normalized key."""

from __future__ import annotations

from models.anchor_mapping import AnchorMapping
from models.anchor_record import AnchorRecord


def build_mappings(
    existing_anchors: list[AnchorRecord],
    new_anchors: list[AnchorRecord],
) -> list[AnchorMapping]:
    existing_by_key: dict[str, AnchorRecord] = {}
    for a in existing_anchors:
        if a.anchor_key not in existing_by_key:
            existing_by_key[a.anchor_key] = a

    new_by_key: dict[str, AnchorRecord] = {}
    for a in new_anchors:
        if a.anchor_key not in new_by_key:
            new_by_key[a.anchor_key] = a

    all_keys: list[str] = []
    seen: set[str] = set()
    for a in existing_anchors:
        if a.anchor_key not in seen:
            all_keys.append(a.anchor_key)
            seen.add(a.anchor_key)
    for a in new_anchors:
        if a.anchor_key not in seen:
            all_keys.append(a.anchor_key)
            seen.add(a.anchor_key)

    mappings: list[AnchorMapping] = []
    for key in all_keys:
        ex = existing_by_key.get(key)
        nw = new_by_key.get(key)
        notes: list[str] = []
        if ex and nw:
            notes.append("auto-matched")
        elif ex and not nw:
            notes.append("existing only")
        else:
            notes.append("new only")

        mappings.append(AnchorMapping(
            anchor_key=key,
            existing_anchor=ex,
            new_anchor=nw,
            include_in_test=bool(ex and nw),
            notes=notes,
        ))

    return mappings


def get_match_status(mapping: AnchorMapping) -> str:
    if mapping.existing_anchor and mapping.new_anchor:
        return "Matched"
    elif mapping.existing_anchor:
        return "Existing Only"
    else:
        return "New Only"
