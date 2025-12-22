import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RulesEngine:
    """Very simple rules evaluator."""

    def __init__(self, rules: List[Dict[str, Any]] | None = None):
        self.rules = rules or []

    def evaluate(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered = []
        for rule in self.rules:
            condition = rule.get("condition")
            try:
                if condition and eval(condition, {}, context):  # pragma: no cover (simple placeholder)
                    triggered.append(rule)
            except Exception as exc:
                logger.debug("Rule evaluation failed: %s", exc)
        return triggered
