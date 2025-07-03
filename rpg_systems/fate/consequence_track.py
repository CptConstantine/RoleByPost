from typing import Any, Dict
from attr import dataclass
from rpg_systems.fate.aspect import Aspect

@dataclass
class Consequence:
    """
    Represents a consequence in a Fate RPG character's consequence track.
    """
    name: str
    severity: int
    aspect: Aspect = None  # Optional aspect associated with the consequence

    def is_filled(self) -> bool:
        return self.aspect is not None and self.severity > 0

class ConsequenceTrack:
    """
    Represents a consequence track for a Fate RPG character.
    """
    def __init__(self, name: str, consequences: list[Consequence]):
        self.name = name
        self.consequences = consequences
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "consequences": [c.__dict__ for c in self.consequences]
        }
    
    @staticmethod
    def from_dict(data: dict) -> "ConsequenceTrack":
        """Create a ConsequenceTrack from a dictionary representation."""
        consequences = []
        for c in data.get("consequences", []):
            # Handle aspect conversion explicitly
            aspect_data = c.get("aspect")
            aspect = Aspect.from_dict(aspect_data) if aspect_data else None
            
            consequence = Consequence(
                name=c.get("name", ""),
                severity=c.get("severity", 0),
                aspect=aspect
            )
            consequences.append(consequence)
        
        return ConsequenceTrack(name=data.get("name", ""), consequences=consequences)

    def add_consequence(self, consequence: Consequence) -> bool:
        if any(c.name == consequence.name for c in self.consequences):
            return False
        self.consequences.append(consequence)
        return True

    def remove_consequence(self, consequence_name: str) -> bool:
        consequence = next((c for c in self.consequences if c.name == consequence_name), None)
        if consequence:
            self.consequences.remove(consequence)
            return True
        return False