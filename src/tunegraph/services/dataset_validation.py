from __future__ import annotations

import math
from typing import Any


class DatasetValidator:
    """Metadata-level validator. File-specific validators can be added through plugins."""

    def validate(
        self,
        *,
        record_count: int,
        content_sha256: str,
        metadata: dict[str, Any],
        checks: list[str],
        minimum_quality_score: float,
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        score = 1.0

        if "schema" in checks and len(content_sha256) != 64:
            findings.append({"severity": "error", "code": "INVALID_DIGEST"})
            score -= 0.5
        if record_count <= 0:
            findings.append({"severity": "warning", "code": "EMPTY_DATASET"})
            score -= 0.25
        if metadata.get("known_duplicates", 0):
            duplicate_count = int(metadata["known_duplicates"])
            ratio = duplicate_count / max(record_count, 1)
            findings.append(
                {"severity": "warning", "code": "DUPLICATES", "ratio": round(ratio, 4)}
            )
            score -= min(0.3, ratio)
        if metadata.get("contains_secrets"):
            findings.append({"severity": "error", "code": "POTENTIAL_SECRETS"})
            score -= 0.5
        if metadata.get("label_conflict_rate") is not None:
            conflict_rate = float(metadata["label_conflict_rate"])
            if math.isnan(conflict_rate) or not 0 <= conflict_rate <= 1:
                findings.append({"severity": "error", "code": "INVALID_CONFLICT_RATE"})
                score -= 0.5
            elif conflict_rate > 0.05:
                findings.append(
                    {
                        "severity": "warning",
                        "code": "LABEL_CONFLICTS",
                        "rate": conflict_rate,
                    }
                )
                score -= min(0.3, conflict_rate)

        score = max(0.0, min(1.0, score))
        blocking = any(item["severity"] == "error" for item in findings)
        return {
            "score": round(score, 4),
            "minimum_score": minimum_quality_score,
            "passed": not blocking and score >= minimum_quality_score,
            "checks": checks,
            "findings": findings,
        }
