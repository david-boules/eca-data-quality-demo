# ECA Data Request Database — Phase 2 Prototype

> New to the project? Start with [SIMPLE_GUIDE.md](SIMPLE_GUIDE.md) for a plain-language explanation and exact commands.

## Purpose and scope

This repository demonstrates a complete local pipeline from fictional company Data Request workbooks to a normalized SQLite database and a searchable Streamlit application. Phase 2 extends—not replaces—the functioning Phase 1 implementation. `create_database.py` remains the authoritative definition of the original 19-table schema.

All companies, people, products, suppliers, countries, workbooks, and transactions are synthetic. The generated workbook format is a demonstration format and is not claimed to reproduce any confidential internal ECA template. This is not production-ready software.

## Architecture

```text
generate_large_dataset.py
        ↓
eca_demo_large.db (synthetic source of truth)
        ↓
reproducibly selected companies
        ↓
one synthetic XLSX Data Request per company
        ↓
READ → STANDARDIZE → VALIDATE → RESOLVE → TRANSFORM → INSERT → VERIFY
        ↓
fresh eca_demo.db (unchanged 19-table schema)
        ↓
database validation + source/target round-trip comparison
        ↓
Streamlit exploration and deterministic analytics
```

SQLite is intentionally retained as the demonstration backend. No cloud service, credentials, authentication provider, external API, or real organizational data is required.

## Data Request mapping

The maintainable field-level mapping is defined once in `data_request_mapping.py` and shared by generator and importer.

| Synthetic workbook area | Database tables |
|---|---|
| Company Info, Financials, Activities, Related Parties | `companies`, `company_financials`, `company_activities`, `related_parties` |
| Products | `products`, `company_products`, `product_alternatives` |
| Customers | `customers` |
| Imports | `imports`, `suppliers` |
| Local Purchases | `purchases`, `suppliers` |
| Costs | `costs` |
| Sales | `sales` |
| Tenders | `tenders`, `tender_items` |
| Exports | `exports` |
| Storage Capacity | `warehouses`, `storage_capacity` |
| Inventory | `inventory` |

The transformation is explicit:

```text
sheet + mapped column → whitespace/date/number standardization
                      → workbook and row validation
                      → product/supplier/customer/warehouse resolution
                      → target table column
```

## Repository structure

- `create_database.py` — authoritative 19-table schema and Phase 1 database creation.
- `populate_database.py` — original small fictional Phase 1 dataset.
- `validate_database.py` — integrity, constraint, and cross-company tests. The duplicate-financial test now selects an existing `(company_id, year)` pair dynamically.
- `sample_queries.py` — original representative Phase 1 SQL.
- `reset_database.py` — removes `eca_demo.db` for a clean rebuild.
- `generate_large_dataset.py` — deterministic large synthetic source database.
- `data_request_mapping.py` — workbook sheets, columns, required fields, and validation categories.
- `generate_data_request_workbooks.py` — deterministic company selection, database extraction, XLSX creation, and selection manifest.
- `import_data_requests.py` — single/batch validation and transactional import with JSON reporting.
- `round_trip_validation.py` — business-key source/target comparisons and representative sales acceptance query.
- `db.py` — context-managed, parameterized query layer for the UI.
- `app.py` — Streamlit application.
- `data_quality.py` — transparent completeness, coverage, database-health, and arithmetic-consistency analysis.
- `anomaly_detection.py` — explainable median/MAD statistical review flags.
- `inject_demo_anomalies.py` — deterministic anomaly-demo copy and JSON manifest generator.
- `launch_app.py` — environment-safe launcher that always uses `.venv` and selects an available local port.
- `assets/eca_logo.png` — public header logo retrieved from the Egyptian Competition Authority website for the local prototype theme.
- `tests/` — automated database, generator, importer, validation, rollback, mapping, round-trip, analytics, and UI smoke tests.

Generated databases, workbook batches, and reports are ignored by Git and can be regenerated.

## Setup

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Dependencies are deliberately limited to XLSX handling, Streamlit, its compatible tabular binary stack, and testing. The app does not import pandas directly; compatible version ranges constrain NumPy, pandas, and PyArrow because Streamlit uses them internally for table rendering.

Use `python3 launch_app.py` when launching. The launcher always delegates to the project virtual environment, even if `python3` itself comes from Anaconda, and selects the next available port when the preferred port is occupied. Mixing global packages directly can produce binary errors such as `numpy.core.multiarray failed to import`; `requirements.txt` constrains a compatible NumPy/Pandas/PyArrow family used internally by Streamlit.

## Phase 1 workflow

The original workflow remains supported:

```bash
python reset_database.py
python create_database.py
python populate_database.py
python validate_database.py
python sample_queries.py
```

## Complete Phase 2 workflow

### 1. Generate the source of truth

```bash
python generate_large_dataset.py --companies 1000 --overwrite
```

The generator reuses `SCHEMA_SQL`, creates globally shared products and suppliers, uses deterministic random data, and validates SQLite integrity, foreign keys, sales ownership, tender ownership, and inventory ownership.

### 2. Generate 100 individual workbooks

```bash
python generate_data_request_workbooks.py --companies 100 --seed 42 --overwrite
```

Output:

```text
synthetic_data_requests/
├── company_0001.xlsx
├── ...
├── company_0100.xlsx
└── selection_manifest.json
```

The manifest records the seed, source database, source company IDs, company names, and file association needed for round-trip verification. Each workbook contains exactly one company plus that company's related records.

### 3. Import into a fresh target

Batch import:

```bash
python import_data_requests.py \
  --directory synthetic_data_requests \
  --db eca_demo.db \
  --report import_report.json \
  --create-fresh
```

Single workbook import:

```bash
python import_data_requests.py --file synthetic_data_requests/company_0001.xlsx --db eca_demo.db
```

Each workbook has its own transaction. A failure rolls back that workbook only and does not affect earlier successful imports. The CLI reports each file and writes a structured JSON summary with files processed, successes, failures, warnings, validation failures, rows inserted, rows rejected, per-table insert counts, and detailed issues.

### 4. Validate and compare

```bash
python validate_database.py
python round_trip_validation.py
```

Round-trip comparison uses company names, product names, customer codes, warehouse names, and other stable synthetic business keys rather than assuming source and target surrogate IDs match. It validates representative field-level records, record counts, and aggregate totals for the selected companies. It does not claim that every field in every row has been exhaustively compared. It also chooses a product/year with imported sales and cross-checks the aggregate across all selected companies.

## Validation behavior

Validation collects multiple issues where practical:

- **Fatal workbook errors:** unreadable XLSX, required sheet/header missing, invalid company cardinality.
- **Row errors:** missing required values, invalid numeric/integer types, negative values, invalid months, excessive returns, duplicate rows, inconsistent metadata for a repeated tender key, conflicting metadata for an exact-name shared product, and unknown product/customer/warehouse relationships. Years must be integer values; the prototype does not impose an additional allowed year range.
- **Warnings:** supported in the report model for non-blocking observations; none are generated for valid empty optional data areas.

Invalid workbooks are never partially retained. SQLite constraints and a post-insert foreign-key check provide a final safety layer inside the transaction.

### Duplicate imports

The prototype deliberately rejects a workbook when its unique synthetic `company_name` already exists in the target. This prevents repeat submissions from double-counting transactional data without extending the 19-table business schema. It is intentionally a small demo strategy—not a production provenance, versioning, or amendment workflow.

### Shared identity resolution

Products and suppliers are reused across companies:

- suppliers resolve by `suppliers.supplier_name`, which is database-unique;
- products resolve by exact `product_name` for this controlled dataset;
- company-product links remain company-specific.

`products.product_name` is not unique in the schema. Exact product-name matching is valid only because `generate_large_dataset.py` creates globally distinct names such as `Synthetic Product 0001`. A production system would require a confirmed product identifier, master-data policy, or entity-resolution process. No fuzzy matching is presented as a production solution.

## Streamlit application

Launch locally:

```bash
python3 launch_app.py
```

The default preferred address is `http://localhost:8501`. If that port is already occupied, the launcher prints the next available address. Always use the address printed in the terminal.

### Safe hosted synthetic demo

The application supports a read-only hosted mode intended only for the bundled synthetic anomaly database:

```bash
ECA_HOSTED_DEMO=1 streamlit run app.py
```

Hosted mode fixes the database selection to `eca_demo_anomaly.db`, removes the workbook import page, and labels the deployment as synthetic. For Streamlit Community Cloud, add `ECA_HOSTED_DEMO="1"` in Advanced settings → Secrets before deployment. Do not deploy real submissions or confidential data using this prototype.

Pages include:

- **Overview:** dynamic counts and year coverage.
- **Company Explorer:** company details and linked financials, activities, products, customers, sales, purchases, imports, exports, inventory, tenders, costs, and storage.
- **Product Explorer:** reporting companies, sales records/totals, and available years.
- **Data Explorer:** bounded dataset selection and SQL-side row limiting.
- **Sales / Market Analysis:** product, actual stored year, and optional company filters; aggregate, supporting rows, and chart.
- **Data Quality / Import Status:** Database Health preserves SQLite integrity, foreign-key, and import-report results; Data Quality shows completeness and arithmetic consistency; Anomaly Review shows explainable statistical review flags with filters and CSV downloads.
- **Import Data:** local XLSX upload through the same validation/import pipeline.
- **System Guide:** the complete plain-language project guide, readable and downloadable inside the application.

All SQL values are parameterized. Table choices are restricted to a fixed allow-list. Year choices come from actual stored data rather than hard-coded UI logic.

## Automated tests

```bash
python -m pytest -q
```

Tests cover clean schema creation, foreign keys, deterministic selection, workbook count/sheets/isolation/source correspondence, single and batch import, missing sheets/values, invalid numeric types, invalid relationships, malformed XLSX, duplicate rejection, rollback, representative mappings, dynamic duplicate-financial validation without 2025, round-trip aggregates, the 2026 sales query, and all Streamlit pages.

## Data quality and anomaly monitoring

These layers are deliberately separate:

- import **validation** decides whether a submitted workbook is structurally and semantically safe to import;
- a **consistency issue** means a stored calculated value does not reconcile with its explicit component fields within ±0.02 currency units;
- a **statistical review flag** means an observation is unusual relative to its product/year comparison group. It is not automatically incorrect and is not evidence of anti-competitive conduct.

`data_quality.py` checks sales, local-purchase, import, tender, and export calculated values; fixed-cost and variable-cost sums; and total production cost. A rule is skipped when any required input or observed value is NULL. It also reports all table record counts, per-field null counts/rates, company coverage, year coverage, SQLite integrity, and foreign-key results. Optional datasets are coverage facts only: a company is not penalized for having no imports, exports, tenders, or related parties, and no opaque overall score is created.

`anomaly_detection.py` checks sales unit price, sales quantity, import CIF price, and local-purchase unit price. For each product/year group with at least 8 non-null observations, it calculates the median, median absolute deviation (MAD), and robust z-score `0.67448975 × (value − median) / MAD`. The default absolute threshold is 3.5. When MAD is zero, observations equal to the median receive zero; any deviation receives signed infinity and is review-flagged. The minimum group size and threshold are configurable function arguments.

Create the controlled demo without changing the clean database:

```bash
python3 inject_demo_anomalies.py \
  --source eca_demo.db \
  --output eca_demo_anomaly.db \
  --manifest anomaly_manifest.json
ECA_DB_PATH=eca_demo_anomaly.db python3 launch_app.py
```

The script verifies the clean file's SHA-256 before and after, preserves schema and foreign keys, and records 12 intended changes plus any ordinary comparison-support rows needed for sparse optional datasets. The demo covers four statistical extremes and all eight arithmetic rules.

## Assumptions and limitations

- SQLite is for a local demonstration, not a confirmed production DBMS.
- All workbook layouts and data are synthetic and not confidential templates.
- Product-name matching is a controlled synthetic assumption only.
- Company-name duplicate rejection does not model amendments, versions, or partial resubmissions.
- Transaction tables intentionally retain the grain supplied by the source generator; not every table has a natural uniqueness constraint.
- Authentication, authorization, encryption, audit logging, deployment, backups, multi-user concurrency, production volumes, licensing, integrations, and exact organizational mapping require confirmed requirements.
- The app is a local prototype and does not implement natural-language-to-SQL.
- Completeness statistics describe presence; they do not establish whether optional data should exist or whether a NULL is substantively acceptable.
- Robust univariate flags do not adjust for contracts, dosage, pack size, geography, seasonality, promotions, company scale, or other legitimate business context. Human review and source-document confirmation are required.
- This module does not perform cartel detection, misconduct classification, legal analysis, or automated enforcement decisions.

## Recommended future work

After organizational requirements are confirmed: define stable master-data identifiers, exact workbook contracts, submission/version provenance, amendment policy, role-based access, security controls, audit history, production DBMS and deployment architecture, migrations, observability, backup/recovery, and broader performance testing.
