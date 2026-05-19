"""Product knowledge memory — accumulates validated data points about products.

After PI Review validates a research brief, verified data points are merged into
a persistent product knowledge base. Cross-run accumulation builds up confidence
when multiple independent research runs agree on the same data point.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

MIN_CONFIDENCE_FOR_STORAGE = 0.6
CONVERGENCE_BOOST = 0.05  # extra confidence when a new source agrees with stored value


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().removesuffix("+00:00") + "Z"


class ProductKnowledgeMemory:
    """In-memory product knowledge base built from validated research data.

    Designed to be serialized into CollaborationState.product_knowledge_memory
    and persisted via LangGraph's checkpointer.

    Usage::

        mem = ProductKnowledgeMemory.from_state(state.get("product_knowledge_memory"))
        updated = mem.ingest_brief(validated_brief, quality_score)
        # → store updated.to_dict() back into state
    """

    def __init__(self, products: dict[str, Any] | None = None) -> None:
        self.products: dict[str, dict[str, Any]] = products or {}

    # ── serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "products": self.products,
            "last_updated": _now_iso(),
        }

    @classmethod
    def from_state(cls, state_data: dict | None) -> ProductKnowledgeMemory:
        if state_data and isinstance(state_data.get("products"), dict):
            return cls(products=state_data["products"])
        return cls()

    # ── ingest ─────────────────────────────────────────────────────────────

    def ingest_brief(
        self,
        validated_brief: dict,
        quality_score: float = 0.5,
    ) -> ProductKnowledgeMemory:
        """Merge validated data points from a research brief into product knowledge.

        Only stores data points with confidence above MIN_CONFIDENCE_FOR_STORAGE.
        When a data point already exists, checks for convergence.
        The product entry is always created (even without verified points) to track
        that the product was researched.
        """
        topic = validated_brief.get("topic", "unknown")
        verified_points: list[dict] = validated_brief.get("verified_data_points", [])

        product = self._ensure_product(topic)

        if not verified_points:
            logger.debug("No verified_data_points in brief for topic=%s", topic)
            product["last_updated"] = _now_iso()
            product["total_ingest_runs"] = product.get("total_ingest_runs", 0) + 1
            return self

        for point in verified_points:
            if not isinstance(point, dict):
                continue
            data = point.get("data", point.get("label", ""))
            if not data:
                continue
            raw_source = point.get("source", "unknown")
            point_confidence = float(point.get("confidence", 0.5))
            run_confidence = min(point_confidence, quality_score)

            if run_confidence < MIN_CONFIDENCE_FOR_STORAGE:
                continue

            attr_key = self._normalize_key(data)
            existing = product["attributes"].get(attr_key)

            if existing:
                # Convergence check: does new value agree with stored value?
                stored_value = existing.get("value")
                new_value = point.get("value")
                if stored_value is not None and new_value is not None:
                    if self._values_match(stored_value, new_value):
                        existing["confidence"] = min(1.0, existing["confidence"] + CONVERGENCE_BOOST)
                        existing["sources"] += 1
                    else:
                        # Divergence: store as alternative, lower confidence
                        alt_key = f"{attr_key}_alt_{existing['sources']}"
                        product["attributes"][alt_key] = {
                            "value": new_value,
                            "unit": point.get("unit", ""),
                            "confidence": run_confidence,
                            "sources": 1,
                            "source_list": [raw_source],
                            "note": f"Diverges from primary value ({stored_value})",
                        }
                else:
                    existing["sources"] += 1
            else:
                product["attributes"][attr_key] = {
                    "value": point.get("value"),
                    "unit": point.get("unit", ""),
                    "confidence": run_confidence,
                    "sources": 1,
                    "source_list": [raw_source],
                }

        product["last_updated"] = _now_iso()
        product["total_ingest_runs"] = product.get("total_ingest_runs", 0) + 1
        return self

    # ── query ──────────────────────────────────────────────────────────────

    def query_product(self, product_name: str) -> dict | None:
        """Return known attributes for a product, or None."""
        for key, prod in self.products.items():
            if product_name.lower() in key.lower() or key.lower() in product_name.lower():
                return prod
        return None

    def get_high_confidence_attributes(
        self, product_name: str, threshold: float = 0.8
    ) -> dict[str, Any]:
        """Return attributes with confidence >= threshold for a product."""
        product = self.query_product(product_name)
        if not product:
            return {}
        return {
            k: v
            for k, v in product.get("attributes", {}).items()
            if not k.endswith("_alt_")  # skip divergence alternatives
            and v.get("confidence", 0) >= threshold
        }

    # ── helpers ────────────────────────────────────────────────────────────

    def _ensure_product(self, topic: str) -> dict[str, Any]:
        key = topic.lower().strip()
        if key not in self.products:
            self.products[key] = {
                "topic": topic,
                "attributes": {},
                "last_updated": None,
                "total_ingest_runs": 0,
            }
        return self.products[key]

    @staticmethod
    def _normalize_key(label: str) -> str:
        """Normalize a data label into a consistent attribute key."""
        key = label.lower().strip().replace(" ", "_").replace("-", "_")
        # Remove common prefixes like "the_", "a_"
        for prefix in ("the_", "a_", "an_"):
            if key.startswith(prefix):
                key = key[len(prefix):]
        return key

    @staticmethod
    def _values_match(a: Any, b: Any) -> bool:
        """Check if two values agree within a reasonable tolerance."""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            # 5% tolerance for numeric values
            if abs(a) < 1e-9:
                return abs(b) < 1e-9
            return abs(a - b) / max(abs(a), abs(b)) < 0.05
        return str(a).lower().strip() == str(b).lower().strip()
