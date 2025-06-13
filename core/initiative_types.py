from typing import Any, Dict, List
from core.abstract_models import BaseInitiative

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
        self.data.setdefault("active", False)
        self.data.setdefault("type", "generic")

    @classmethod
    def from_participants(cls, participants: List[Dict[str, Any]]):
        data = {
            "participants": participants,
            "remaining_in_round": [p["id"] for p in participants],
            "current_index": 0,
            "round_number": 1,
            "active": False,
            "type": "generic"
        }
        return cls(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericInitiative":
        return cls(data)

    @property
    def participants(self):
        return self.data["participants"]

    @property
    def current_index(self):
        return self.data.get("current_index", 0)

    @current_index.setter
    def current_index(self, value):
        self.data["current_index"] = value

    @property
    def is_active(self):
        return self.data.get("active", 0)

    @is_active.setter
    def is_active(self, value):
        self.data["active"] = value

    @property
    def current(self):
        if self.participants and 0 <= self.current_index < len(self.participants):
            return self.participants[self.current_index]["id"]
        return None

    def advance_turn(self):
        if not self.participants:
            return
        self.current_index += 1
        if self.current_index >= len(self.participants):
            self.current_index = 0
            self.round_number += 1

    def to_dict(self):
        return self.data

    def get_participant_name(self, user_id):
        for p in self.participants:
            if p["id"] == user_id:
                return p["name"]
        return "Unknown"

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
    def from_participants(cls, participants: List[Dict[str, Any]]):
        """
        Create a new PopcornInitiative with the given participants and first turn.
        """
        data = {
            "participants": participants,
            "remaining_in_round": [p["id"] for p in participants],
            "current": None,
            "last": None,
            "type": "popcorn",
            "round_number": 1
        }
        return cls(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PopcornInitiative":
        return cls(data)

    @property
    def participants(self):
        return self.data["participants"]

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

    def to_dict(self):
        return self.data

    def advance_turn(self, next_id: str):
        """
        Advance to the next turn, chosen by the current player.
        """
        if next_id in self.remaining_in_round:
            self.remaining_in_round.remove(next_id)
        self.last = self.current
        self.current = next_id

        # If no one is left, start a new round and increment round_number
        if not self.remaining_in_round:
            self.round_number += 1
            # Allow anyone (including the last person) to be picked first
            self.remaining_in_round = [p["id"] for p in self.participants]
            self.last = None  # Last resets for new round

    def is_round_end(self):
        """
        Returns True if the round is ending (no one left in remaining_in_round).
        """
        return not self.remaining_in_round

    def get_participant_name(self, user_id):
        for p in self.participants:
            if p["id"] == user_id:
                return p["name"]
        return "Unknown"