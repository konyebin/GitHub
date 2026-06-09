---
name: kb-builder
description: |
  Build a structured knowledge base from live web research. Accepts a topic
  and focus area, searches multiple authoritative sources, extracts key facts,
  deduplicates and cross-validates findings, scores confidence, and saves a
  refined .md knowledge base document ready for use by other skills or agents.
  Use when you need grounded, up-to-date reference material for recommendations,
  thresholds, playbooks, or advisory content.
allowed-tools: WebSearch, WebFetch, Read, Write, Bash
argument-hint: [topic] [focus-area] [output-path]
---

# KB Builder Skill

Researches a topic across the web and produces a refined, structured knowledge
base document. The output is designed to be consumed by other skills, agents,
or recommendation engines — not just stored.

---

## When to invoke

- "build a knowledge base on X"
- "research best practices for Y and save them"
- "get current benchmarks / industry standards for Z"
- "build a recommendation engine for [existing report/skill]"
- Any time a skill's advice is generic and should be grounded in real data

---

## Process (always follow this order)

### Phase 1 — Scope

Before searching, define:
1. **Topic** — what domain (e.g. "Webex Calling call queue operations")
2. **Focus** — what questions the KB must answer (e.g. "root causes and fixes for high abandon rates")
3. **Audience** — who reads it (practitioner, executive, automated recommendation engine)
4. **Output path** — where to save the .md file
5. **Depth** — quick (5–8 sources) / standard (10–15) / deep (20+)

Ask the user to confirm scope before Phase 2 if any of these is ambiguous.

### Phase 2 — Search

Issue **3–5 targeted searches** covering:
- Industry benchmark/standard sources (Gartner, Forrester, ICMI, HDI, Cisco, IEEE)
- Vendor documentation (Cisco Help, Webex docs, RFCs)
- Practitioner forums and case studies (Cisco Community, Reddit r/networking, Stack Exchange)
- Academic or standards bodies where relevant

Search query patterns:
```
"[topic] best practices site:cisco.com OR site:help.webex.com"
"[metric] industry benchmark [year]"
"[symptom] root cause resolution enterprise voice"
"[topic] SLA standard contact center ICMI OR HDI"
```

Deduplicate queries — do not search the same angle twice.

### Phase 3 — Fetch & Extract

For each promising result, `WebFetch` the page and extract:
- Specific numeric benchmarks (with source + date)
- Root cause → resolution mappings
- Configuration recommendations with specifics (not vague advice)
- Contradictions between sources (flag these explicitly)
- Version/platform constraints (e.g. "applies to Webex Calling, not CUCM")

Discard:
- Marketing content with no data
- Paywalled content (note the existence but don't speculate on content)
- Sources older than 3 years unless they're foundational standards

### Phase 4 — Refine

Apply these rules before writing the KB:

**Deduplication:** If two sources say the same thing, keep the most specific + most recent. Cite both.

**Contradiction resolution:**
- If two authoritative sources disagree on a threshold, keep both with a "Sources disagree" note and explain the likely context difference (industry, org size, etc.)
- Never silently pick one

**Confidence scoring:** Tag each fact:
- `[HIGH]` — multiple independent sources agree, recent, specific
- `[MED]` — single source or older data, plausible but unverified
- `[LOW]` — one source, indirect, inferred, or dated

**Actionability filter:** Every fact must answer "so what?" If it can't drive a decision or recommendation, cut it.

### Phase 5 — Write KB document

Structure:

```markdown
# Knowledge Base: [Topic]
**Built:** YYYY-MM-DD  |  **Sources:** N  |  **Depth:** quick/standard/deep
**Focus:** [the specific questions this KB answers]

---

## Executive Summary
2–4 sentences: what this KB establishes and the single most important finding.

---

## Benchmarks & Thresholds
| Metric | Industry Standard | Source | Confidence |
|--------|------------------|--------|-----------|
| ...    | ...              | ...    | [HIGH]    |

---

## Root Cause → Resolution Playbook
### [Issue Name]
**Symptoms:** ...
**Root causes (ranked by frequency):**
1. ...
2. ...
**Resolution steps:**
- [ ] Step 1 (specific, actionable)
- [ ] Step 2
**Webex-specific commands / config paths:** (if applicable)
**Time to resolve:** ...
**Escalation trigger:** ...

(repeat for each issue type)

---

## Configuration Best Practices
Specific settings, values, and patterns — not generic advice.

---

## What the Data Cannot Tell You
Gaps, caveats, and cases where this KB's advice does not apply.

---

## Sources
| # | URL | Date accessed | Reliability |
|---|-----|--------------|-------------|
| 1 | ... | ...          | Primary/Secondary/Community |
```

### Phase 6 — Save & cross-reference

1. Save the KB to the specified output path
2. If the KB was built for a specific skill, add a reference line to that skill's SKILL.md:
   ```
   See also: `[path/to/kb.md]` — built YYYY-MM-DD, covers [topic]
   ```
3. Report: N sources fetched, N facts extracted, N contradictions flagged, confidence distribution

---

## Quality gates (check before delivering)

- [ ] Every benchmark has a source citation and date
- [ ] No "best practice" without a specific value or step
- [ ] Contradictions are flagged, not silently resolved
- [ ] Confidence scores present on all facts
- [ ] Webex-specific config paths present where the KB is for a Webex skill
- [ ] "What the data cannot tell you" section present
- [ ] Output path saved and confirmed

---

## Existing knowledge bases (do not re-research, extend instead)

| KB | Path | Built | Covers |
|---|---|---|---|
| Misc Report Recommendations | `wxops/docs/knowledge-base/misc-report-recommendations.md` | 2026-05-21 | All 9 misc report sections: industry benchmarks, root cause playbooks, Webex-specific fix paths, QoS config, recording compliance, capacity planning |

---

## Example invocations

```
/kb-builder "Webex Calling call queue operations" "why callers abandon and how to fix it" \
  ~/Documents/GitHub/wxops/docs/knowledge-base/call-queue-optimization.md

/kb-builder "enterprise voice call quality" "packet loss and jitter root causes + fixes" \
  ~/Documents/GitHub/wxops/docs/knowledge-base/call-quality-resolution.md

/kb-builder "contact center SLA compliance" "industry benchmarks and queue staffing models" \
  ~/Documents/GitHub/wxops/docs/knowledge-base/sla-compliance-standards.md
```
