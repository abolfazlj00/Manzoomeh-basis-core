from context import Context
from .predicate import Predicate
from typing import Any


class HasValue (Predicate):
    """Create has value cheking predicate"""

    def __init__(self, expression: str) -> None:
        super().__init__(expression)

    def check(self, context: Context) -> bool:
        try:
            value = eval(self.exprossion, {}, {"context": context})
            return False if not value or value.isspace() else True
        except:
            return False
