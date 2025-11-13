# rule_layer/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .models import RuleResult


class BaseRule(ABC):
    """Abstract base class for all rule implementations."""

    #: Unique identifier for the rule (override in subclasses)
    id: str = ""
    #: Human-readable rule name/title (override in subclasses)
    name: str = ""

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "id", None):
            raise TypeError(f"{cls.__name__} must define a non-empty 'id'")
        if not getattr(cls, "name", None):
            raise TypeError(f"{cls.__name__} must define a non-empty 'name'")

    @abstractmethod
    def evaluate(self, graph: Dict[str, Any]) -> List[RuleResult]:
        """Evaluate the rule against the canonical building graph."""

    def describe(self) -> Dict[str, Any]:
        """Return metadata about the rule for catalogue/discovery purposes."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.__doc__,
            "parameters": self._list_parameters(),
        }

    # ---- helper hooks -------------------------------------------------
    def _list_parameters(self) -> Dict[str, Any]:
        """Inspect configurable attributes that should be exposed."""
        params: Dict[str, Any] = {}
        for attr in dir(self):
            if attr.startswith("_") or attr in {"id", "name", "describe", "evaluate"}:
                continue
            value = getattr(self, attr)
            if isinstance(value, (int, float, str, bool)):
                params[attr] = value
        return params
