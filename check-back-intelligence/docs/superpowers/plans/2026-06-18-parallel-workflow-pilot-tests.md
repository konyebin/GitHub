# Plan: Expand unit tests (parallel workflow pilot)

**Project:** check-back-intelligence  
**Goal:** Add focused unit tests for three independent pure-function modules to validate the coordinator + parallel scouts + sequential builders workflow.

## File map

| Task | Owns (read) | Owns (write) | Tag |
|------|-------------|--------------|-----|
| 1 | `src/ingest/install_base_mapper.py` | `tests/test_mapper.py` | sequential |
| 2 | `src/workbook/note_parser.py` | `tests/test_note_parser.py` | sequential |
| 3 | `src/workbook/subscription_dates.py` | `tests/test_subscription_dates.py` | sequential |
| Scout A | `src/ingest/` | — | parallel-safe |
| Scout B | `src/workbook/note_parser.py` | — | parallel-safe |
| Scout C | `src/workbook/subscription_dates.py` | — | parallel-safe |

No file overlap between implementation tasks.

## Scout phase (parallel-safe)

Three explore agents report testable functions, edge cases, and recommended assertions. Read-only.

## Implementation tasks

### Task 1 — install_base_mapper tests

Extend `tests/test_mapper.py`:

- `_first_number` with commas, currency, multi-token strings
- `_format_license` MT/DI combinations and empty inputs
- `map_row` entitled license from Cloud Calling Billed Seats
- Medium-confidence gap entries for review-flagged fields

**Verify:** `cd check-back-intelligence && python tests/test_mapper.py`

### Task 2 — note_parser tests

Create `tests/test_note_parser.py`:

- `parse_prof_ws_shorthand` and `apply_prof_ws_shorthand_from_cells`
- `parse_notes_to_structured` for license pairs, feature counts, trends, Connected-UC
- `compute_active_pct` plain counts vs complex license strings

**Verify:** `cd check-back-intelligence && python tests/test_note_parser.py`

### Task 3 — subscription_dates tests

Create `tests/test_subscription_dates.py`:

- `derive_subscription_dates` from start + term months
- Preserve existing range text and verified overrides path (unit-level only)
- `_parse_single_date` format variants

**Verify:** `cd check-back-intelligence && python tests/test_subscription_dates.py`

## Integration

Run all three test files in one command:

```bash
cd check-back-intelligence && python tests/test_mapper.py && python tests/test_note_parser.py && python tests/test_subscription_dates.py
```

## Deliverables beyond tests

- `.cursor/skills/parallel-dev-workflow/SKILL.md` — reusable workflow skill
- `AGENTS.md` registration
