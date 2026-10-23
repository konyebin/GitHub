# sf-sandbox: Salesforce-Behavior Access Sandbox (Design Spec)

Status: draft for review. No implementation exists yet.

## 1. Purpose

A local simulator that reproduces Salesforce's access-control and API behavior so associate engineers can practice and be tested against it. It does not reproduce the Salesforce product feature set. All data is synthetic test data.

"Salesforce behavior" means three things:

1. The security model: who can see and change what, and in which order the layers are evaluated.
2. The REST and query surface: URL shapes, JSON shapes, IDs, pagination and error payloads that a Salesforce client would recognize.
3. Silent-versus-loud semantics: queries silently drop records and fields the user cannot see, while direct access to a hidden record or a forbidden write fails with a specific error.

## 2. Non-goals

- Apex, triggers, flows, validation rules, formulas, Lightning UI, Bulk/Composite/Tooling/Metadata APIs, reports, real OAuth.
- Multi-tenancy, performance parity, governor limits other than the two listed in section 6.
- Any real customer data. Seed data is generated and fake only.

## 3. Stack and layout

Python 3.13, FastAPI, SQLite (stdlib `sqlite3`), PyYAML, pytest. No external services. No secrets: each persona gets a static dev token defined in the policy config or an environment variable, never committed with real values.

```
sf-sandbox/
  CLAUDE.md, README.md
  policy/            YAML source of truth (schema, security, personas, seed)
  src/sfsandbox/
    ids.py           15/18-char ID generation and key prefixes
    policy.py        load + validate policy YAML into typed models
    engine.py        pure permission engine (no I/O)
    store.py         SQLite data layer + share tables
    soql.py          SOQL-subset parser and compiler
    api.py           FastAPI app (REST surface, error mapping)
    audit.py         access-decision log
    scenarios.py     scenario runner
    cli.py           serve, reset, whoami, query, run-scenarios, audit
  tests/
```

Each unit has one job: `engine.py` decides, `store.py` persists, `soql.py` parses, `api.py` translates. `engine.py` never touches the database; it is handed the facts it needs.

## 4. Security model (evaluation order)

For each request the persona (a User) is resolved first, then these layers apply in order.

**4.1 User gate.** User must be active and the effective permissions must include the system permission `ApiEnabled`. Otherwise `403 API_DISABLED_FOR_ORG`-style failure (see error table).

**4.2 Effective permissions.** A user has exactly one Profile and zero or more Permission Sets (and Permission Set Groups, which are bundles of sets). Effective permissions are the union of the profile and all assigned sets. There are no deny rules. This additive behavior is the most important Salesforce semantic to get right.

Supported system permissions: `ApiEnabled`, `ViewAllData`, `ModifyAllData`, `ViewSetup`. `ViewAllData` grants read on every record of every object; `ModifyAllData` grants all CRUD on every record. Both bypass sharing but not field-level security.

**4.3 Object permissions.** Per object: Create, Read, Edit, Delete, ViewAll, ModifyAll. Edit requires Read; Delete requires Read and Edit; ViewAll requires Read; ModifyAll requires ViewAll, Edit and Delete. These dependencies are validated at policy load time, as Salesforce enforces them.

**4.4 Field-level security.** Per field: Read, Edit (Edit implies Read). Fields without Read are removed from query results and record payloads, and cannot be referenced in a query. Fields without Edit cannot be written. Required fields and system fields (`Id`, `OwnerId`, `CreatedDate`, etc.) follow Salesforce rules: system fields are read-only; `OwnerId` is writable only with the right object permission.

**4.5 Record-level access.** Applied only to records, after the object gate.

- Organization-wide default (OWD) per object: `Private`, `PublicReadOnly`, `PublicReadWrite`, `ControlledByParent`.
- Owner always has full access to their own records (subject to object permissions).
- Role hierarchy: users in roles above a record owner get the same access as the owner, when the object has "grant access using hierarchies" enabled (default true).
- Sharing rules: owner-based (records owned by role/group X shared to role/group Y) and criteria-based (records matching field criteria shared to a role/group), each with Read or Read/Write.
- Manual shares: explicit per-record grants, stored in a share table.
- `ViewAll` / `ModifyAll` on the object, and the system permissions in 4.2, override record sharing.
- Effective record access is the maximum across all sources; the minimum is `None`.

**4.6 Result of a check.** The engine returns `Decision(allowed, layer, reason)` where `layer` is one of `user`, `object`, `field`, `record` and `reason` is a human-readable string. Every decision is written to the audit log.

## 5. API surface

Base path `/services/data/v62.0/`. Auth header `Authorization: Bearer <persona token>`.

| Method and path | Behavior |
|---|---|
| `GET /sobjects/{Type}/{id}` | One record, fields filtered by FLS |
| `POST /sobjects/{Type}` | Create, returns `{id, success, errors}` |
| `PATCH /sobjects/{Type}/{id}` | Update, 204 on success |
| `DELETE /sobjects/{Type}/{id}` | Delete, 204 on success |
| `GET /query?q=...` | SOQL subset, paginated |
| `GET /query/{cursor}` | Next page (`nextRecordsUrl`) |
| `GET /sobjects/{Type}/describe` | Describe limited to objects and fields the user can read |
| `GET /sobjects` | Objects the user can read |

Sandbox-only extras (not Salesforce): `GET /sandbox/audit`, `POST /sandbox/reset`, `GET /sandbox/whoami`.

**IDs.** 18-character case-safe IDs with the standard key prefixes: `001` Account, `003` Contact, `006` Opportunity, `500` Case, `005` User, `00E` Role, `00e` Profile, `0PS` Permission Set. Input accepts 15 or 18 characters.

**Record payload.** `{"attributes": {"type": "Account", "url": "/services/data/v62.0/sobjects/Account/001..."}, "Id": "...", ...}`.

**Query response.** `{"totalSize": n, "done": true|false, "nextRecordsUrl": "...", "records": [...]}`. Page size 2000.

**Errors.** A JSON array: `[{"message": "...", "errorCode": "...", "fields": []}]`.

### 5.1 Silent versus loud (the behaviors learners must internalize)

| Situation | Behavior |
|---|---|
| Query touches records the user cannot see | Records silently omitted; `totalSize` reflects only visible rows |
| Query selects a field with no read access | `400 INVALID_FIELD` ("No such column ... on entity ...") |
| Query on an object with no Read | `400 INVALID_TYPE` ("sObject type ... is not supported") |
| GET by ID of a record the user cannot see | `404 NOT_FOUND` |
| PATCH or DELETE on visible but not editable record | `403 INSUFFICIENT_ACCESS_OR_READONLY` |
| Write to a field without Edit | `400 INVALID_FIELD_FOR_INSERT_UPDATE` |
| POST without Create on the object | `403 INSUFFICIENT_ACCESS_OR_READONLY` |
| Bad token | `401 INVALID_SESSION_ID` |
| User lacks `ApiEnabled` | `403 API_DISABLED_FOR_ORG` |

Fidelity note: error codes and message wording above come from the author's knowledge of Salesforce and must be verified against Salesforce documentation or a real developer org before the error table is treated as authoritative. Mismatches are fixed in `api.py`'s single error-mapping function, so correction is a one-place change.

## 6. SOQL subset

Supported: `SELECT <fields | COUNT()> FROM <Object> [WHERE ...] [ORDER BY field [ASC|DESC]] [LIMIT n] [OFFSET n]`. Conditions: `=`, `!=`, `<`, `<=`, `>`, `>=`, `LIKE`, `IN`, `NOT IN`, `AND`, `OR`, `NOT`, parentheses, literals (strings, numbers, booleans, `null`, dates). Parent relationship fields via dot notation (`Account.Name`), where FLS applies to the parent field and the parent record sharing applies to the parent.

Unsupported constructs raise a clear `MALFORMED_QUERY` error rather than guessing. No subqueries, GROUP BY, aggregate functions beyond `COUNT()`, or SOSL in v1.

Governor-style limits kept for realism: 2000 rows per query page, and a configurable daily API request cap per persona that returns `REQUEST_LIMIT_EXCEEDED`.

## 7. Data and seed

Objects for v1: Account, Contact, Opportunity, Case, User, plus one custom object (`Project__c`) so learners see custom-field behavior. Seed data is generated deterministically from a fixed random seed so test results are reproducible, and is designed so that every persona has some visible and some hidden records.

## 8. Personas

Defined in `policy/personas.yaml`. v1 set: System Administrator, Sales Manager (role above the associates), Support Agent, and three associate engineer variants:

- **Associate Engineer, Read-Only:** read on most objects, no create/edit/delete, sensitive fields (for example `Opportunity.Amount`, `Account.AnnualRevenue`) hidden by FLS, OWD Private except where shared.
- **Associate Engineer, Contributor:** read plus create/edit on the custom object and edit on own Cases; no delete.
- **Associate Engineer, Elevated:** Contributor plus one permission set that grants temporary read on a sensitive object, to demonstrate additive permission sets.

These start as defaults and are meant to be edited in YAML.

## 9. Audit log and scenarios

Every engine decision is recorded with timestamp, persona, action, object, record ID if any, allow or deny, layer and reason. `GET /sandbox/audit` filters by persona and outcome.

A scenario is a YAML file: persona, request, expected status and expected error code or expected visible fields and row count. `run-scenarios` executes them and prints pass/fail. The initial scenarios cover each row of the section 5.1 table and each persona.

## 10. Testing strategy

1. Engine unit tests: a generated persona x object x operation matrix compared against an explicit expected table kept in the repo.
2. Sharing tests: OWD, role hierarchy, sharing rules, manual shares, View All and Modify All, including the "maximum across sources" rule.
3. FLS tests: field omission in responses, `INVALID_FIELD` in queries, write rejection.
4. SOQL parser tests, including every unsupported construct producing `MALFORMED_QUERY`.
5. API tests for every row in section 5.1 and for pagination.
6. Scenario suite run in CI.

## 11. Build order (becomes the implementation plan)

1. Project scaffold, IDs, policy schema and loader with validation.
2. Permission engine with the matrix test.
3. Data layer, seed, reset.
4. Record-level sharing in the engine and store.
5. SOQL parser and compiler with security filtering.
6. REST API and error mapping.
7. Audit log and sandbox endpoints.
8. Scenario runner, CLI, and docs.

Steps 2 and 5 are independent once step 1 is done and are good candidates for parallel sub-agents.

## 12. Open items

- Verify the error table in section 5.1 against real Salesforce behavior.
- Decide whether v1 includes parent-relationship queries (currently included) or defers them.
- Confirm the exact FLS defaults for the three associate variants.
