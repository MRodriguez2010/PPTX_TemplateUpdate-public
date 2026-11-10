from dataclasses import dataclass, field


@dataclass
class AnchorRecord:
    anchor_key: str
    slide_index: int
    shape_name: str
    detection_source: str
    visible_text: str
    left: int
    top: int
    width: int
    height: int
    notes: list[str] = field(default_factory=list)
