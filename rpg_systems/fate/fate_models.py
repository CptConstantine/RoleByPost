from typing import Dict, Any, Optional

class Aspect:
    """
    Represents a Fate aspect with standard properties and formatting methods.
    Used for character aspects, scene aspects, and potentially zone aspects.
    """
    def __init__(self, 
                 name: str = "", 
                 description: str = "", 
                 is_hidden: bool = False, 
                 free_invokes: int = 0,
                 owner_id: Optional[str] = None):
        """
        Initialize an Aspect object.
        
        Args:
            name: The name/title of the aspect
            description: Optional longer description or notes about the aspect
            is_hidden: Whether this aspect is hidden from non-GM players
            free_invokes: Number of free invocations available on this aspect
            owner_id: Optional ID of the entity that owns this aspect (character, scene, etc.)
        """
        self.name = name
        self.description = description
        self.is_hidden = is_hidden
        self.free_invokes = free_invokes
        self.owner_id = owner_id
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Aspect':
        """
        Create an Aspect object from a dictionary representation.
        Handles both current and legacy format.
        
        Args:
            data: Dictionary containing aspect data
            
        Returns:
            Aspect: An initialized Aspect object
        """
        if isinstance(data, str):
            # Legacy format - just a string
            return cls(name=data)
        
        # Current dict format
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            is_hidden=data.get("is_hidden", False),
            free_invokes=data.get("free_invokes", 0),
            owner_id=data.get("owner_id")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Aspect to a dictionary for storage.
        
        Returns:
            Dict: Dictionary representation of the aspect
        """
        data = {
            "name": self.name,
            "description": self.description,
            "is_hidden": self.is_hidden,
            "free_invokes": self.free_invokes
        }
        
        if self.owner_id:
            data["owner_id"] = self.owner_id
            
        return data
        
    def get_full_aspect_string(self, is_gm: bool = False, is_owner: bool = False) -> str:
        """
        Get a formatted string with all aspect details, respecting visibility rules.
        
        Args:
            is_gm: Whether the viewer is a GM
            is_owner: Whether the viewer owns this aspect
            
        Returns:
            str: Formatted aspect string
        """
        # Hidden aspects are only shown to GMs and owners
        if self.is_hidden and not (is_gm or is_owner):
            return ""
            
        # Start with the name
        result = f"**{self.name}**"
        
        # Mark hidden aspects (only visible to GMs and owners)
        if self.is_hidden:
            result = f"*{result} (hidden)*"
            
        # Add description if available
        if self.description:
            result += f": {self.description}"
            
        # Add free invokes if any are available
        if self.free_invokes > 0:
            result += f" [{self.free_invokes} free invoke{'s' if self.free_invokes > 1 else ''}]"
            
        return result
    
    def get_short_aspect_string(self, is_gm: bool = False, is_owner: bool = False) -> str:
        """
        Get a short formatted string with just the name and free invokes.
        
        Args:
            is_gm: Whether the viewer is a GM
            is_owner: Whether the viewer owns this aspect
            
        Returns:
            str: Short formatted aspect string or empty string if hidden and not visible
        """
        # Hidden aspects are only shown to GMs and owners
        if self.is_hidden and not (is_gm or is_owner):
            return ""
            
        # Start with name, possibly marking as hidden for GMs and owners
        if self.is_hidden:
            result = f"*{self.name}* (hidden)"
        else:
            result = self.name
            
        # Add free invokes if any
        if self.free_invokes > 0:
            result += f" [{self.free_invokes}]"
            
        return result
    
    def invoke(self, count: int = 1) -> bool:
        """
        Use one or more free invokes on this aspect.
        
        Args:
            count: Number of invokes to use
            
        Returns:
            bool: True if successful, False if not enough free invokes
        """
        if count > self.free_invokes:
            return False
            
        self.free_invokes -= count
        return True
        
    def add_free_invoke(self, count: int = 1) -> None:
        """
        Add one or more free invokes to this aspect.
        
        Args:
            count: Number of invokes to add
        """
        self.free_invokes += count
        
    def clear_free_invokes(self) -> None:
        """Reset free invokes to zero."""
        self.free_invokes = 0
        
    def __str__(self) -> str:
        """String representation of the aspect (for logging/debugging)"""
        hidden_marker = "[HIDDEN] " if self.is_hidden else ""
        invoke_str = f" [{self.free_invokes}]" if self.free_invokes > 0 else ""
        desc_str = f": {self.description}" if self.description else ""
        return f"{hidden_marker}{self.name}{invoke_str}{desc_str}"
        
    def __eq__(self, other) -> bool:
        """Check if two aspects are equal"""
        if not isinstance(other, Aspect):
            return False
        return (self.name == other.name and 
                self.description == other.description and 
                self.is_hidden == other.is_hidden and 
                self.free_invokes == other.free_invokes)