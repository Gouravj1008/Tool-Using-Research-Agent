"""Bounded storage for compact research findings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


DEFAULT_MAX_FINDINGS = 20
DEFAULT_MAX_CHARS = 30_000
DEFAULT_MAX_FINDING_CHARS = 2_000


@dataclass(frozen=True)
class Finding:
    """A compact, source-backed research finding."""

    source_id: str
    url: str
    title: str
    finding: str
    claims: tuple[str, ...]
    query: str | None = None


class Scratchpad:
    """Store bounded findings separately from raw conversation content."""

    def __init__(
        self,
        *,
        max_findings: int = DEFAULT_MAX_FINDINGS,
        max_chars: int = DEFAULT_MAX_CHARS,
        max_finding_chars: int = DEFAULT_MAX_FINDING_CHARS,
    ) -> None:
        if max_findings < 1 or max_chars < 1 or max_finding_chars < 1:
            raise ValueError("Scratchpad limits must be positive.")
        self.max_findings = max_findings
        self.max_chars = max_chars
        self.max_finding_chars = max_finding_chars
        self._findings: list[Finding] = []

    def add_finding(
        self,
        *,
        url: str,
        title: str,
        finding: str,
        claims: list[str] | tuple[str, ...],
        query: str | None = None,
        source_id: str | None = None,
    ) -> str:
        """Add a compact finding and evict oldest findings when bounded."""
        if not url.strip() or not finding.strip():
            raise ValueError("URL and finding must not be empty.")
        normalized_claims = tuple(
            claim.strip() for claim in claims if isinstance(claim, str) and claim.strip()
        )
        resolved_source_id = source_id or self.source_id_for(url)
        compact_finding = self._truncate(" ".join(finding.split()))
        compact_title = self._truncate(" ".join(title.split()), 300)
        self._findings.append(
            Finding(
                source_id=resolved_source_id,
                url=url.strip(),
                title=compact_title,
                finding=compact_finding,
                claims=normalized_claims,
                query=query.strip() if isinstance(query, str) and query.strip() else None,
            )
        )
        self._trim()
        return resolved_source_id

    def entries(self) -> list[dict[str, Any]]:
        """Return structured findings without raw page content."""
        return [asdict(finding) for finding in self._findings]

    def render_context(self) -> str:
        """Render compact findings for the next model request."""
        return "\n".join(
            json.dumps(entry, ensure_ascii=True, separators=(",", ":"))
            for entry in self.entries()
        )

    def clear(self) -> None:
        """Discard all stored findings."""
        self._findings.clear()

    @staticmethod
    def source_id_for(url: str) -> str:
        """Return a stable non-secret identifier for a source URL."""
        return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:12]

    def _truncate(self, value: str, limit: int | None = None) -> str:
        max_chars = limit or self.max_finding_chars
        return value if len(value) <= max_chars else value[:max_chars].rstrip() + "..."

    def _trim(self) -> None:
        while len(self._findings) > self.max_findings or len(self.render_context()) > self.max_chars:
            self._findings.pop(0)
