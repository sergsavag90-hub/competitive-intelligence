import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class AutoInsights:
    """Rule-based significant changes + LLM summary placeholder."""

    def __init__(self, llm=None, threshold: float = 0.2):
        self.llm = llm
        self.threshold = threshold

    def filter_significant(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [c for c in changes if abs(c.get("change", 0)) >= self.threshold]

    async def summarize(self, changes: List[Dict[str, Any]]) -> str:
        if not self.llm:
            return "LLM not configured"
        prompt = f"Проаналізуй зміни: {changes}"
        return await self.llm.analyze(prompt)
