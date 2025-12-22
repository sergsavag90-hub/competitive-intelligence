"""
Apollo Federation helper for exporting Strawberry schema as a subgraph.
"""

from __future__ import annotations

import strawberry
from strawberry.federation import Schema

from src.graphql.schema import Query, Mutation, Subscription


def build_federated_schema() -> Schema:
    """
    Build a federated schema that can be served by an ASGI app (e.g., via strawberry.asgi).
    """
    return strawberry.federation.Schema(query=Query, mutation=Mutation, subscription=Subscription)
