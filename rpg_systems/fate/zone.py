from dataclasses import dataclass, field
from typing import List, Dict, Any
from .aspect import Aspect, AspectType

@dataclass
class Zone:
    name: str
    description: str = ""
    aspects: List[Aspect] = field(default_factory=list)
    special_properties: Dict[str, Any] = field(default_factory=dict)
    
    def add_aspect(self, aspect: Aspect) -> None:
        aspect.aspect_type = AspectType.ZONE
        aspect.zone_name = self.name
        self.aspects.append(aspect)
    
    def remove_aspect(self, aspect_name: str) -> bool:
        for i, aspect in enumerate(self.aspects):
            if aspect.name == aspect_name:
                del self.aspects[i]
                return True
        return False
    
    def get_aspect_strings(self, is_gm: bool = False) -> List[str]:
        return [aspect.get_full_aspect_string(is_gm=is_gm) for aspect in self.aspects if aspect.get_full_aspect_string(is_gm=is_gm)]