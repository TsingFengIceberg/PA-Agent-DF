"""Collaboration Memory — extends DeerFlow Memory with collaboration-specific dimensions.

Two memory tracks:
- SourceCredibilityMemory: tracks domain/source reliability based on verification outcomes
- ProductKnowledgeMemory: accumulates validated product data points across research runs
"""

from __future__ import annotations

from .product_knowledge import ProductKnowledgeMemory
from .source_credibility import SourceCredibilityMemory

__all__ = [
    "SourceCredibilityMemory",
    "ProductKnowledgeMemory",
]
