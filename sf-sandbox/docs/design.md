# sf-sandbox: A Salesforce-Style Learning App (Design Spec)

Status: draft for review. No implementation exists yet.

## 1. Purpose

A small local app that behaves like Salesforce so associate engineers can see how Salesforce works, then use it for projects and guided activities. It reproduces how Salesforce is organized and how users work in it. It does not reproduce the product's size or its security and administration depth.

All data is synthetic test data. There is no authentication, no permissions, no profiles, no sharing and no field-level security. Everyone who opens the app can do everything.

## 2. What associates should learn from it

The app is built to make these Salesforce ideas visible and hands-on:

1. **Everything is an object with fields.** Standard objects (Account, Contact, Lead, Opportunity, Case, Task) and custom objects (`Thing__c`) with custom fields (`Field__c`).
2. **Metadata drives the app.** Adding an object or field in setup immediately changes the forms, list views and API. Nothing is hard-coded per object.
3. **Records relate to each other.** Lookup fields, related lists, and a parent record page that shows its children.
4. **Users find and work with records.** Record pages, list views with filters, global search, create/edit/delete.
5. **Rules shape data.** Required fields, picklists, and validation rules that block a save with a message.
6. **Data is reachable as code.** A SOQL console and a Salesforce-shaped REST API, which is what engineers actually use.
7. **Summaries.** Simple reports (tabular and grouped) and dashboard tiles.

## 3. Non-goals

Security of any kind, Apex, triggers, flows, Lightning components, real OAuth, multi-user collaboration, Bulk/Composite/Metadata APIs, email, files, Chatter, and real Salesforce compatibility. Where Salesforce is deep (for example formulas or automation), v1 offers one small, teachable slice.

## 4. Stack and layout

Python 3.13, FastAPI, Jinja2 templates with HTMX for interactivity (no JavaScript build step), SQLite via the stdlib `sqlite3`, PyYAML, pytest. Runs with one command and no external services.

```
sf-sandbox/
  CLAUDE.md, README.md
  seed/                  YAML: object metadata, sample records
  labs/                  YAML + markdown activities and project templates
  src/sfsandbox/
    ids.py               Salesforce-style 18-char IDs with key prefixes
    metadata.py          object/field definitions: load, validate, persist
    store.py             generic record storage driven by metadata
    rules.py             required, picklist and validation-rule evaluation
    soql.py              SOQL-subset parser and executor
    reports.py           tabular and grouped reports
    api.py               REST surface (Salesforce-shaped JSON)
    ui/                  routes, templates and static assets
    labs.py              activity runner and checkers
    cli.py               serve, reset, seed, export, import
  tests/
```

Each unit has one purpose. `store.py` knows nothing about HTTP; `api.py` and `ui/` both call the same store and rules, so the UI and API always agree.

## 5. Data model (metadata-driven)

Metadata lives in SQLite tables (`sf_object`, `sf_field`, `sf_picklist_value`, `sf_validation_rule`, `sf_list_view`, `sf_report`) and is seeded from `seed/*.yaml`. Records of every object live in one generic table keyed by object name with a JSON payload, plus indexed lookup columns, so adding a field never needs a schema migration.

Field types in v1: Text, Text Area, Number, Currency, Percent, Date, Date/Time, Checkbox, Picklist, Email, Phone, URL, Lookup (to any object), and Auto Number. A simple Formula field (read-only, evaluated from same-record fields with `+ - * / & IF()`) is included as the single formula example.

Every record has `Id` (18-character, with the standard prefixes: `001` Account, `003` Contact, `00Q` Lead, `006` Opportunity, `500` Case, `00T` Task), `Name` where applicable, `CreatedDate`, `LastModifiedDate`. Custom objects get a generated key prefix starting with `a0`.

Standard objects ship pre-defined with realistic fields and relationships (Contact to Account, Opportunity to Account, Case to Account and Contact, Task to any record). Associates can add fields to standard objects or create custom objects.

## 6. Features

### 6.1 Setup (Object Manager lite)
Create an object, add or edit fields, edit picklist values, define a page layout as an ordered list of sections and fields, and define related lists. Changes take effect immediately in the UI and API. Deleting a field or object soft-deletes it so a lab can be reset cleanly.

### 6.2 Working with records
- Record page: highlights panel, detail sections from the layout, related lists with "New" buttons that prefill the lookup.
- Create, edit, delete with inline validation messages, and a delete confirmation that mentions child records.
- Recently viewed.

### 6.3 List views and search
- List views per object with filter (field, operator, value, AND logic), sort, visible columns and a row limit. Associates can create their own.
- Inline edit of cells in a list view.
- Global search across Name and key text fields of all objects, grouped by object.

### 6.4 Rules
- Required fields and picklist restriction.
- Validation rules: an expression (the same small expression language as the formula field) that, when true, blocks the save and shows an error message at the top or on a field.

### 6.5 SOQL console and REST API
Base path `/services/data/v62.0/`: `GET/POST /sobjects/{Type}`, `GET/PATCH/DELETE /sobjects/{Type}/{id}`, `GET /sobjects/{Type}/describe`, `GET /query?q=`, with Salesforce-shaped JSON (`attributes`, `totalSize`, `done`, `records`, error array). Describe is generated from metadata, so custom objects and fields appear automatically.

SOQL subset: `SELECT fields | COUNT() FROM Object WHERE ... ORDER BY ... LIMIT ... OFFSET ...`, comparison operators, `LIKE`, `IN`, `AND/OR/NOT`, parent fields by dot notation (`Account.Name`), and one level of child subquery (`(SELECT Id FROM Contacts)`). Unsupported syntax returns a clear `MALFORMED_QUERY` message that says what is not supported. The console shows results as a table and as raw JSON.

### 6.6 Reports and dashboards
Tabular reports (object, columns, filters, sort) and summary reports (one grouping, with count, sum or average). A dashboard is a page of up to six tiles (number, table or bar chart) each backed by a report.

### 6.7 Activities (Task object)
Tasks and logged calls attach to any record and appear in an Activity section on the record page. This is the same Task object an associate can query.

## 7. Projects and activities

This is the part that makes the app a training tool.

**Lab format.** A lab is a folder in `labs/` with `lab.yaml` (title, objective, prerequisites, estimated steps) and a markdown walkthrough. Each step has a goal in plain language and optional hints.

**Checks.** A step completes when its check passes. Checks are declarative and evaluated against the live app state: an object exists, a field of a given type exists, a picklist has these values, a record matching a SOQL condition exists, a SOQL query returns an expected row count, a validation rule rejects a given record, a list view or report exists. This is how "did you really build it" is verified.

**Learners.** No login. A learner enters a name; progress is stored per name. Several associates can use one running instance, or each can run their own.

**Project templates.** Larger exercises with a starting data set and a rubric, for example "Support Desk" (custom objects, lookups, validation, list views, a report) and "Sales Pipeline Cleanup" (find and fix bad data using SOQL and list views).

**Reset.** `sfsandbox reset` returns the app to seed state. A lab can also declare its own starter state, which is loaded when the lab starts.

**Starter labs (v1):** (1) tour of the objects and a record page; (2) create and edit records, relate a Contact to an Account; (3) list views and search; (4) build a custom object with fields and a lookup; (5) validation rules; (6) SOQL basics; (7) REST API basics with `curl`; (8) build a report.

## 8. Seed data

Deterministic synthetic data from a fixed random seed: a few hundred Accounts and related Contacts, Opportunities, Cases and Tasks, with realistic variety and a handful of intentionally dirty records for cleanup activities. No real customer data is ever used.

## 9. Testing strategy

1. Metadata tests: adding, editing and deleting objects and fields flows through store, API and describe.
2. Store tests: CRUD and lookup behavior for standard and custom objects.
3. Rules tests: required fields, picklists, validation expression language.
4. SOQL tests: each supported construct and every unsupported construct producing `MALFORMED_QUERY`.
5. API tests for Salesforce-shaped payloads and describe output.
6. UI tests: route-level tests for record pages, list views and search; a few browser smoke tests.
7. Lab tests: each starter lab has a script that performs the steps through the API and asserts every check passes, so labs cannot silently rot.

## 10. Build order (becomes the implementation plan)

1. Scaffold, IDs, metadata schema, seed loader.
2. Generic store with lookups and related records.
3. Rules and the expression language (also used by formula fields).
4. SOQL parser and executor.
5. REST API and describe.
6. UI: record page, create/edit, related lists, recently viewed.
7. List views, inline edit and global search.
8. Setup UI (objects, fields, layouts).
9. Reports and dashboards.
10. Lab runner, checks, and starter labs.
11. Docs and facilitator guide.

After step 2, steps 3 and 4 are independent and good candidates for parallel sub-agents; steps 6 to 9 can also be split once the API is stable.

## 11. Open items

- Whether the UI should visually imitate Lightning (look and feel) or use a neutral clean style. Default: Salesforce-like layout and vocabulary, neutral styling, no copied assets.
- Whether labs should run per-learner instances or one shared instance. Default: shared instance with per-name progress.
- Final list of starter labs and project templates.
