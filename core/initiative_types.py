from typing import Any, Dict, List
from core.models import BaseInitiative, InitiativeParticipant

class GenericInitiative(BaseInitiative):
    """
    Generic initiative: GM sets the order, and turns proceed in that order.
    """
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self.data.setdefault("participants", [])  # List of dicts, in order
        self.data.setdefault("remaining_in_round", [])
        self.data.setdefault("current_index", 0)
        self.data.setdefault("round_number", 1)
        self.data.setdefault("is_started", False)
        self.data.setdefault("type", "generic")

    @classmethod
    def from_participants(cls, participants: List[InitiativeParticipant]):
        data = {
            "participants": [p.to_dict() for p in participants],
            "remaining_in_round": [p.id for p in participants],  # <-- use .id, not ["id"]
            "current_index": 0,
            "round_number": 1,
            "is_started": False,
            "type": "generic"
        }
        return cls(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data = data.copy()
        return cls(data)

    @property
    def current_index(self):
        return self.data.get("current_index", 0)

    @current_index.setter
    def current_index(self, value):
        self.data["current_index"] = value

    @property
    def is_started(self):
        return bool(self.data.get("is_started", False))

    @is_started.setter
    def is_started(self, value):
        self.data["is_started"] = value

    @property
    def current(self):
        if self.participants and 0 <= self.current_index < len(self.participants):
            return self.participants[self.current_index].id
        return None

    def advance_turn(self):
        if not self.participants:
            return
        self.current_index += 1
        if self.current_index >= len(self.participants):
            self.current_index = 0
            self.round_number += 1

class PopcornInitiative(BaseInitiative):
    """
    Popcorn initiative: GM picks who goes first. Each person picks the next.
    """
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self.data.setdefault("participants", [])
        self.data.setdefault("remaining_in_round", [])
        self.data.setdefault("current", None)
        self.data.setdefault("last", None)
        self.data.setdefault("round_number", 1)  # Ensure round_number is always present

    @classmethod
    def from_participants(cls, participants: List[InitiativeParticipant]):
        """
        Create a new PopcornInitiative with the given participants and first turn.
        """
        data = {
            "participants": [p.to_dict() for p in participants],
            "remaining_in_round": [p.id for p in participants],  # <-- use .id
            "current": None,
            "last": None,
            "type": "popcorn",
            "round_number": 1
        }
        return cls(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data = data.copy()
        data["participants"] = [InitiativeParticipant.from_dict(p) if isinstance(p, dict) else p for p in data.get("participants", [])]
        return cls(data)

    @property
    def remaining_in_round(self):
        return self.data["remaining_in_round"]

    @remaining_in_round.setter
    def remaining_in_round(self, value):
        self.data["remaining_in_round"] = value

    @property
    def current(self):
        return self.data["current"]

    @current.setter
    def current(self, value):
        self.data["current"] = value

    @property
    def last(self):
        return self.data["last"]

    @last.setter
    def last(self, value):
        self.data["last"] = value

    def advance_turn(self, next_id: str):
        """
        Advance to the next turn, chosen by the current player.
        """
        if not self.remaining_in_round:
            self.remaining_in_round = [p.id for p in self.participants]

        if next_id in self.remaining_in_round:
            self.remaining_in_round.remove(next_id)
        self.last = self.current
        self.current = next_id

        # If no one is left, start a new round and increment round_number
        if len(self.remaining_in_round) == len(self.participants) - 1:
            self.round_number += 1
        if not self.remaining_in_round:
            self.last = None  # Last resets for new round

    def is_round_end(self):
        """
        Returns True if the round is ending (no one left in remaining_in_round).
        """
        return not self.remaining_in_round