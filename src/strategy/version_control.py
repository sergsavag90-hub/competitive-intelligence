"""
Simple git-like version control for pricing strategies with branching and merge requests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyVersion:
    name: str
    content: Dict
    parent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)


class StrategyRepository:
    def __init__(self):
        self.branches: Dict[str, StrategyVersion] = {"main": StrategyVersion(name="main", content={"pricing": "default"})}

    def create_branch(self, name: str, from_branch: str = "main", content: Optional[Dict] = None) -> StrategyVersion:
        base = self.branches.get(from_branch)
        if not base:
            raise ValueError(f"Base branch {from_branch} not found")
        version = StrategyVersion(name=name, content=content or base.content.copy(), parent=from_branch)
        self.branches[name] = version
        logger.info("Created strategy branch %s from %s", name, from_branch)
        return version

    def merge_branch(self, source: str, target: str = "main") -> StrategyVersion:
        if source not in self.branches or target not in self.branches:
            raise ValueError("Source or target branch not found")
        merged_content = self.branches[target].content.copy()
        merged_content.update(self.branches[source].content)
        merged = StrategyVersion(name=target, content=merged_content, parent=source, metadata={"merged_at": datetime.utcnow().isoformat()})
        self.branches[target] = merged
        logger.info("Merged %s into %s", source, target)
        return merged

    def get_branch(self, name: str = "main") -> StrategyVersion:
        return self.branches[name]
