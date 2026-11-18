"""Checks that the leadership-facing `plain` field of every finding is jargon-free."""
import re

BANNED = [r"\bAUC\b", r"\brho\b", r"\bSpearman\b", r"\bKendall\b", r"\bCI\b", r"confidence interval", r"\bbootstrap",
          r"\bpermutation\b", r"\bperm\b", r"\bp[-= ]?value", r"\bp\s*[=<]", r"\bq\s*[=<]", r"\bBH\b", r"\bICC\b",
          r"Mann-Whitney", r"silhouette", r"\bridge\b", r"\bPCA\b", r"\bARI\b", r"epsilon", r"\bvariance\b",
          r"percentile", r"range-restricted", r"cross-validated", r"\bpartial\b", r"\bresidual", r"\btau\b",
          r"\brobust\b", r"\bsuggestive\b", r"\bweak\b", r"candidate\d+", r"\bR-squared\b", r"\bodds\b", r"\blexicon\b"]
MAX_WORDS = 60


def problems(plain: str) -> list[str]:
    out = [f"banned term /{b}/" for b in BANNED if re.search(b, plain, re.I)]
    if len(plain.split()) > MAX_WORDS:
        out.append(f"{len(plain.split())} words (max {MAX_WORDS})")
    return out
