from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class StressBox:
    value: int
    is_filled: bool = False

class StressTrack:
    def __init__(self, track_name: str, boxes: list[StressBox], linked_skill: str = None):
        self.track_name = track_name
        self.boxes = boxes
        self.linked_skill = linked_skill
    
    def to_dict(self):
        """Convert the stress track to a dictionary representation."""
        return {
            "track_name": self.track_name,
            "boxes": [{"value": box.value, "is_filled": box.is_filled} for box in self.boxes],
            "linked_skill": self.linked_skill
        }

    @staticmethod
    def from_dict(data: dict):
        """Create a StressTrack from a dictionary representation."""
        boxes = [StressBox(**box) for box in data.get("boxes", [])]
        return StressTrack(
            track_name=data.get("track_name", ""),
            boxes=boxes,
            linked_skill=data.get("linked_skill")
        )

    def add_box(self, value: int, is_filled: bool = False):
        """Add a new box to the stress track."""
        self.boxes.append(StressBox(value, is_filled))

    def fill_box(self, index: int):
        """Fill a box in the stress track."""
        if 0 <= index < len(self.boxes):
            self.boxes[index].is_filled = True

    def clear_box(self, index: int):
        """Clear a box in the stress track."""
        if 0 <= index < len(self.boxes):
            self.boxes[index].is_filled = False

    def clear_all_boxes(self):
        """Clear all boxes in the stress track."""
        for box in self.boxes:
            box.is_filled = False