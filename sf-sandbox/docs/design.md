# sf-sandbox: A Read-Only Salesforce-Style Learning App (Design Spec)

Status: draft for review. No implementation exists yet.

## 1. Purpose

A small local app that looks and behaves like Salesforce so associate engineers can see how Salesforce works, then use it for projects and guided activities. Associates explore a ready-made org: they browse, search, filter, query and report on it. They do not change it.

All data is synthetic test data. There is no authentication, no permissions, no profiles, no sharing and no field-level security.

## 2. Read-only rule

The org (its metadata and its records) is read-only to everyone who uses the web UI or the API. There is no create, edit or delete anywhere in either. Write requests to the API return `405 METHOD_NOT_ALLOWED` with a message saying the sandbox is read-only.

Two things are deliberately separate from the org and are writable, so activities still work:

1. **Learner workspace:** per-name progress, submitted answers, and saved SOQL queries, list views and reports. These live in a separate SQLite file (`workspace.db`) and never touch org data.
2. **Operator tooling:** the CLI loader (section 7) is the only way data enters the org. It is run by whoever administers the sandbox, not exposed over HTTP.

The web server opens the org database read-only at the SQLite level (`mode=ro`), so read-only is enforced by the database, not just by missing buttons.

Decision to confirm: saved queries, views and reports are allowed in the learner workspace. If you want nothing saved at all, drop the workspace and keep only progress.

## 3. What associates should learn from it

1. **Everything is an object with fields.** Standard objects (Account, Contact, Lead, Opportunity, Case, Task) and custom objects (`Thing__c`) with custom fields (`Field__c`).
2. **Metadata describes the org.** Object, field, picklist, relationship and validation-rule definitions are all inspectable in an Object Manager style browser, and the same definitions drive the record pages and API.
3. **Records relate to each other.** Lookup fields, related lists, and a parent record page showing its children.
4. **Finding things.** Record pages, list views with filters, global search.
5. **Data is reachable as code.** A SOQL console and a Salesforce-shaped REST API (read only), which is what engineers use.
6. **Summaries.** Reports (tabular and grouped) and dashboard tiles.

## 4. Non-goals

Security of any kind, any write path in the UI or API, Apex, triggers, flows, Lightning components, real OAuth, multi-user collaboration, Bulk/Composite/Metadata APIs, email, files, Chatter, and real Salesforce compatibility.

## 5. Stack and layout

Python 3.13, FastAPI, Jinja2 templates with HTMX (no JavaScript build step), SQLite via the stdlib `sqlite3`, PyYAML, pytest. One command to run, no external services.

```
sf-sandbox/
  CLAUDE.md, README.md
  datasets/<pack>/       dataset packs: metadata + records (section 7)
  labs/                  activities and project templates
  src/sfsandbox/
    ids.py               Salesforce-style 18-char IDs with key prefixes
    metadata.py          object/field definitions: load, validate
    store.py             read-only record access driven by metadata
    loader.py            operator-only writes: validate and load packs/CSV
    rules.py             required, picklist and validation-rule evaluation
    soql.py              SOQL-subset parser and executor
    reports.py           tabular and grouped reports
    api.py               read-only REST surface
    ui/                  routes, templates, static assets
    labs.py              activity runner and checkers
    workspace.py         learner progress and saved items (workspace.db)
    cli.py               serve, load, import, generate, export, snapshot, reset
  tests/
```

`store.py` exposes only read functions. `loader.py` is the only module that writes the org database, and it is imported by `cli.py` only, never by `api.py` or `ui/`.

## 6. Data model

Metadata lives in SQLite tables (`sf_object`, `sf_field`, `sf_picklist_value`, `sf_validation_rule`, `sf_list_view`, `sf_report`). Records of every object live in one generic table keyed by object name, with a JSON payload and indexed lookup columns, so a dataset pack can add a field without a schema migration.

Field types: Text, Text Area, Number, Currency, Percent, Date, Date/Time, Checkbox, Picklist, Email, Phone, URL, Lookup (to any object), Auto Number, and a read-only Formula field (evaluated from same-record fields with `+ - * / & IF()`).

Every record has `Id` (18-character with the standard prefixes: `001` Account, `003` Contact, `00Q` Lead, `006` Opportunity, `500` Case, `00T` Task), `CreatedDate`, `LastModifiedDate`. Custom objects get a generated key prefix starting with `a0`.

Standard objects ship with realistic fields and relationships: Contact to Account, Opportunity to Account, Case to Account and Contact, Task to any record. Validation rules are stored and shown on the object detail page with their error messages, and are enforced when the loader inserts data (so the sandbox can demonstrate what a rule does, and bad records only enter on purpose, see 7.4).

## 7. How data gets in

Data enters only through the operator CLI, in four ways. All of them run the same loader, which validates required fields, picklist values, lookups and validation rules before writing.

### 7.1 Dataset packs (primary)
A pack is a folder under `datasets/<name>/`:

```
datasets/support-desk/
  pack.yaml            name, description, load order, dependencies
  objects.yaml         objects, fields, picklists, relationships, validation rules,
                       list views, reports, page layouts
  records/
    Account.csv
    Contact.csv
    Case.csv           one CSV per object; header row = field API names
```

`sfsandbox load datasets/support-desk` creates the metadata and loads the records. Packs are plain text, so they are easy to review, version in git and share. A lab names the pack it needs, so each activity gets the data it was written for.

### 7.2 CSV import (Data Loader style)
`sfsandbox import --object Contact contacts.csv` adds records to an existing object. Lookups are written as an external key rather than an ID: a column such as `Account.ExternalId__c` is resolved to the real Account ID, as with Salesforce's Data Loader. Rows that fail validation are written to an `errors.csv` next to the input with a reason per row, and the rest still load (`--strict` aborts instead). This is also how an operator can show associates how real data loads behave.

### 7.3 Synthetic generator
`sfsandbox generate --pack support-desk --accounts 300 --seed 42` produces realistic records deterministically from a fixed seed, so the same command always yields the same org. Volume is configurable for list view, report and SOQL exercises.

### 7.4 Intentional messiness
Packs can mark a CSV as `allow_invalid: true` for specific records, which bypasses validation rules for those rows only. This produces duplicates, missing fields and inconsistent values for data-quality activities, and is the only way invalid data gets in.

### 7.5 Housekeeping
- `sfsandbox snapshot <name>` and `sfsandbox reset <name>` save and restore a copy of the org database, so a class can start from a known state.
- `sfsandbox export --object Account out.csv` writes records back out.
- The running server sees newly loaded data without a restart, because SQLite readers see committed writes.

## 8. Features (all read-only)

### 8.1 Browsing
- Record pages: highlights panel, detail sections from the pack's layout, related lists, activity timeline. No New, Edit or Delete buttons.
- Recently viewed (stored in the learner workspace).
- Object browser: object list, fields with types, picklist values, relationships, validation rules, and a diagram of lookups between objects.

### 8.2 List views and search
- Pack-defined list views with filter, sort, columns and row limit.
- Ad hoc filtering and sorting on top of any list view without saving it. Associates can save a view to their own workspace.
- Global search across Name and key text fields of all objects, grouped by object.

### 8.3 SOQL console and REST API
Base path `/services/data/v62.0/`, `GET` only: `/sobjects`, `/sobjects/{Type}/{id}`, `/sobjects/{Type}/describe`, `/query?q=`, with Salesforce-shaped JSON (`attributes`, `totalSize`, `done`, `records`, error array). Describe is generated from metadata.

SOQL subset: `SELECT fields | COUNT() FROM Object WHERE ... ORDER BY ... LIMIT ... OFFSET ...`, comparison operators, `LIKE`, `IN`, `AND/OR/NOT`, parent fields by dot notation (`Account.Name`), and one level of child subquery (`(SELECT Id FROM Contacts)`). Unsupported syntax returns a clear `MALFORMED_QUERY` message. The console shows a table and raw JSON, and queries can be saved to the workspace.

### 8.4 Reports and dashboards
Pack-defined tabular and summary reports (one grouping, with count, sum or average) that associates can run and re-filter. A dashboard is a page of up to six tiles (number, table or bar chart), each backed by a report.

## 9. Projects and activities

Because the org is read-only, activities are about understanding and analyzing it, not building in it.

**Lab format.** A folder in `labs/` with `lab.yaml` (title, objective, required dataset pack, steps) and a markdown walkthrough.

**Checks.** A step is answered in the app and checked automatically. Check types: submit a SOQL query whose result matches an expected result set; enter a numeric or text answer to a question about the data; pick the record that satisfies a description; choose the correct field type or relationship for a described situation; save a list view or report to the workspace whose filters match the requirement. Expected answers are computed from the loaded pack, so they stay correct when the pack changes.

**Learners.** No login. A learner enters a name; progress and saved items are stored per name in the workspace.

**Starter labs (v1):**
1. Tour of the org: objects, fields, record pages, related lists.
2. Reading relationships: follow lookups from Contact to Account to Opportunity.
3. List views and search: find specific records with filters.
4. Metadata detective: identify field types, picklists and validation rules and say what they do.
5. SOQL basics, then SOQL across relationships.
6. REST API basics with `curl`.
7. Reports: answer questions with a tabular and a summary report.
8. Data quality: find the duplicates and bad records in a messy pack (see 7.4).

**Project templates:** "Support Desk analysis" (find backlog, repeat customers and slow cases using SOQL and reports) and "Sales pipeline review" (build the list views and reports a sales manager would ask for, with deliverables checked against the data).

If associates should also build objects, fields and records themselves, that needs a separate writable sandbox mode, which this spec does not include.

## 10. Testing strategy

1. Read-only enforcement: API write methods return 405, and the web process cannot write the org database even if code tried.
2. Loader tests: valid and invalid rows, lookup resolution by external key, `errors.csv` output, `allow_invalid` bypass, validation rule enforcement.
3. Pack tests: every shipped pack loads cleanly from an empty database, and generator output is identical for the same seed.
4. Store, rules and SOQL tests: each supported construct, each unsupported construct producing `MALFORMED_QUERY`.
5. API tests for Salesforce-shaped payloads and describe output.
6. UI route tests and a few browser smoke tests.
7. Lab tests: each starter lab has a script that submits the correct answers through the app and asserts every check passes, so labs cannot silently rot.

## 11. Build order (becomes the implementation plan)

1. Scaffold, IDs, metadata schema, read-only database connection.
2. Loader with validation, dataset pack format, and the first pack with the generator.
3. Read-only store with lookups and related records.
4. SOQL parser and executor.
5. Read-only REST API and describe.
6. UI: record page, related lists, object browser.
7. List views and global search.
8. Reports and dashboards.
9. Workspace, lab runner, checks and starter labs.
10. CSV import, snapshot and reset, export, and docs for operators.

After step 3, steps 4 and 6 are independent and good candidates for parallel sub-agents.

## 12. Open items

- Confirm that saving queries, views and reports to the learner workspace is acceptable under "read-only" (section 2).
- UI styling: Salesforce-like layout and vocabulary with neutral styling and no copied assets (default).
- Shared instance with per-name progress (default) versus one instance per learner.
- Which dataset packs ship first (default: Support Desk, plus a Sales pipeline pack).
