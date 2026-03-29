from __future__ import annotations


class NotFoundFlag:
    """
    Sentinel value used to indicate that a value was not found.
    
    This class serves as a special marker object that can be returned
    when a search or lookup operation fails. It is always falsy and
    compares equal to other NotFoundFlag instances or the NotFoundFlag type.
    """

    def __eq__(self, other: NotFoundFlag) -> bool:
        """
        Compare this instance with another object.
        
        Returns True if other is a NotFoundFlag instance or the NotFoundFlag type,
        False otherwise. This allows checking for "not found" using either
        `result == NotFoundFlag` or `result == NotFoundFlag()`.
        
        Args:
            other: Object to compare with
            
        Returns:
            True if other is NotFoundFlag or NotFoundFlag type, False otherwise
        """
        if type(other) == NotFoundFlag or (type(self) == type(other()) if type(other) == type else None):
            return True
        return False

    def __bool__(self) -> bool:
        """
        Return the boolean value of this instance.
        
        Always returns False, making NotFoundFlag instances falsy.
        This allows using NotFoundFlag in boolean contexts like:
        `if not result:` or `if result: ... else: ...`
        
        Returns:
            Always False
        """
        return False
