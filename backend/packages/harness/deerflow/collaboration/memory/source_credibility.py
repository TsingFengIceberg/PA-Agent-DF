"""Source credibility memory — tracks data source reliability based on verification outcomes.

Each source domain accumulates a credibility score updated by Critic challenges and
Meta-Judge rulings. Sources verified as accurate gain score; sources with unresolved
or dismissed challenges lose score.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Score adjustment weights
RESOLVED_BOOST = 0.05  # score increase when challenge resolved (source vindicated)
UNRESOLVED_PENALTY = 0.10  # score decrease when challenge unresolved
DISMISSED_PENALTY = 0.02  # small penalty for dismissed (still noise)
DEFAULT_SCORE = 0.50  # neutral starting score for unknown domains
MIN_SCORE = 0.0
MAX_SCORE = 1.0


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().removesuffix("+00:00") + "Z"


def _extract_domain(source: dict | str) -> str | None:
    """Extract a normalised domain key from a source reference."""
    if isinstance(source, str):
        raw = source
    elif isinstance(source, dict):
        raw = source.get("source", source.get("url", source.get("domain", "")))
    else:
        return None
    if not raw:
        return None
    # Strip protocol, path, and www prefix
    raw = raw.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    domain = raw.split("/")[0].split("?")[0].split("#")[0]
    return domain.strip().rstrip(".") or None


def _clamp(score: float) -> float:
    return max(MIN_SCORE, min(MAX_SCORE, score))


class SourceCredibilityMemory:
    """In-memory tracker for source domain credibility.

    Designed to be serialized into CollaborationState.source_credibility_memory
    and persisted via LangGraph's checkpointer.

    Usage::

        mem = SourceCredibilityMemory.from_state(state.get("source_credibility_memory"))
        updated = mem.apply_ruling(ruling, scout_results)
        # → store updated.to_dict() back into state
    """

    def __init__(self, domains: dict[str, Any] | None = None) -> None:
        self.domains: dict[str, dict[str, Any]] = domains or {}

    # ── serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains": self.domains,
            "last_updated": _now_iso(),
        }

    @classmethod
    def from_state(cls, state_data: dict | None) -> SourceCredibilityMemory:
        if state_data and isinstance(state_data.get("domains"), dict):
            return cls(domains=state_data["domains"])
        return cls()

    # ── score access ───────────────────────────────────────────────────────

    def get_score(self, domain: str) -> float:
        """Return the credibility score for a domain (0.0–1.0)."""
        entry = self.domains.get(domain)
        return entry["score"] if entry else DEFAULT_SCORE

    def get_all_scores(self) -> dict[str, float]:
        return {d: e["score"] for d, e in self.domains.items()}

    # ── update from ruling ─────────────────────────────────────────────────

    def apply_ruling(self, ruling: dict, scout_results: list[dict]) -> SourceCredibilityMemory:
        """Update source scores based on a Meta-Judge ruling.

        - resolved challenges → sources gain credibility
        - unresolved challenges → sources lose credibility
        - dismissed challenges → slight penalty
        """
        resolved = ruling.get("resolved", [])
        unresolved = ruling.get("unresolved", [])
        dismissed = ruling.get("dismissed", [])

        # Collect domains from scout results
        for sr in scout_results:
            source = sr.get("source", "")
            domain = _extract_domain(source)
            if not domain:
                continue

            entry = self._ensure_entry(domain)
            entry["last_verified"] = _now_iso()

            # Did this source survive verification?
            # Resolved = source was challenged but data held up → boost
            # Unresolved = challenge couldn't be resolved → penalty
            if any(self._domain_matches(r, domain) for r in resolved):
                entry["score"] = _clamp(entry["score"] + RESOLVED_BOOST)
                entry["verified_count"] += 1
            elif any(self._domain_matches(u, domain) for u in unresolved):
                entry["score"] = _clamp(entry["score"] - UNRESOLVED_PENALTY)
                entry["failed_count"] += 1

        # Dismissed challenges — minor penalty for noise
        for d in dismissed:
            domain = _extract_domain(d.get("data_source", ""))
            if domain:
                entry = self._ensure_entry(domain)
                entry["score"] = _clamp(entry["score"] - DISMISSED_PENALTY)

        self._prune_stale()
        return self

    def apply_challenges(self, challenges: list[dict]) -> SourceCredibilityMemory:
        """Record that challenges were filed against sources (pre-ruling).

        Does not change scores — only records the event for audit trail.
        """
        for ch in challenges:
            evidence = ch.get("evidence", [])
            for ev in (evidence if isinstance(evidence, list) else [evidence]):
                domain = _extract_domain(ev)
                if domain:
                    entry = self._ensure_entry(domain)
                    topics = entry.setdefault("sample_topics", [])
                    claim = ch.get("claim", "")
                    if claim and claim not in topics:
                        topics.append(claim)
        return self

    # ── helpers ────────────────────────────────────────────────────────────

    def _ensure_entry(self, domain: str) -> dict[str, Any]:
        if domain not in self.domains:
            self.domains[domain] = {
                "score": DEFAULT_SCORE,
                "verified_count": 0,
                "failed_count": 0,
                "last_verified": None,
                "sample_topics": [],
            }
        return self.domains[domain]

    @staticmethod
    def _matches(resolved_item: dict | str, source: str) -> bool:
        """Check if a resolved/unresolved item references the given source."""
        if isinstance(resolved_item, str):
            return resolved_item in source or source in resolved_item
        # dict form: {challenge_id, issue, reason, ...}
        return bool(
            (resolved_item.get("challenge_id") or "") in source
            or source in (resolved_item.get("issue") or "")
            or source in (resolved_item.get("reason") or "")
        )

    @staticmethod
    def _domain_matches(item: dict | str, domain: str) -> bool:
        """Check if a resolved/unresolved item references the given domain."""
        if isinstance(item, str):
            return domain in item
        text_fields = [item.get("issue", ""), item.get("reason", ""), item.get("challenge_id", "")]
        return any(domain in field for field in text_fields if field)

    def _prune_stale(self, max_entries: int = 200) -> None:
        """Remove domains with the lowest (verified_count - failed_count) delta."""
        if len(self.domains) <= max_entries:
            return
        sorted_domains = sorted(
            self.domains.items(),
            key=lambda kv: (kv[1].get("verified_count", 0) - kv[1].get("failed_count", 0)),
        )
        to_remove = sorted_domains[: len(self.domains) - max_entries]
        for domain, _ in to_remove:
            del self.domains[domain]
        logger.debug("Pruned %d stale source entries", len(to_remove))
