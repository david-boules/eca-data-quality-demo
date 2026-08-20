# ECA Data Request Prototype — Simple Guide

## 1. What did we build?

We built a local demonstration showing how Excel Data Request responses from many companies can be collected into one searchable database.

The complete process is:

```text
Create fictional company data
        ↓
Choose 100 fictional companies
        ↓
Create one Excel workbook for each company
        ↓
Check every workbook for errors
        ↓
Import valid workbooks into SQLite
        ↓
Compare the imported data with the original data
        ↓
Explore the results in a Streamlit application
```

Everything is synthetic. No real company data, confidential ECA files, credentials, or external services are used.

## 2. Why are there two databases?

### `eca_demo_large.db` — the source database

This contains the large fictional dataset created by `generate_large_dataset.py`.

Think of it as the correct answer or source of truth. We select companies from this database and turn their records into Excel workbooks.

### `eca_demo.db` — the imported target database

This is the database populated from the generated Excel workbooks.

After importing the workbooks, we compare this database with `eca_demo_large.db`. If the values match, the Excel export/import process worked correctly.

Both databases use the same original 19-table schema from `create_database.py`.

## 3. What is inside one workbook?

Each generated `.xlsx` file represents exactly one fictional company.

It contains these sheets:

| Sheet | Information represented |
|---|---|
| Company Info | Basic company information |
| Financials | Annual financial records |
| Activities | Company activities |
| Related Parties | Related fictional organizations |
| Products | Products reported by the company |
| Customers | The company's fictional customers |
| Imports | Imported purchases |
| Local Purchases | Purchases from local suppliers |
| Costs | Product-related costs |
| Sales | Sales to customers |
| Tenders | Tenders and tender items |
| Exports | Export transactions |
| Storage Capacity | Warehouses and annual capacity |
| Inventory | Products stored in warehouses |

These sheets are a synthetic demonstration design. They are not copies of confidential internal templates.

## 4. What happens during an import?

For every workbook, the importer follows this sequence:

```text
Read the workbook
        ↓
Standardize values
        ↓
Validate sheets, columns, and rows
        ↓
Resolve shared products and suppliers
        ↓
Transform workbook rows into database rows
        ↓
Insert everything in one transaction
        ↓
Check foreign keys
        ↓
Commit on success or roll back on failure
```

A transaction means that one workbook is imported completely or not at all. If an error occurs halfway through, rows from that workbook are removed automatically. Previously successful workbooks remain intact.

## 5. What validation is performed?

The importer checks for problems such as:

- missing required sheets;
- missing or renamed columns;
- missing required values;
- text entered where a number is required;
- non-integer year values or months outside 1–12;
- negative quantities or monetary values;
- returned quantities greater than sold quantities;
- duplicate rows;
- conflicting non-null metadata when an exact-name shared product already exists;
- inconsistent tender type, entity, or date across rows using the same tender key;
- references to products, customers, or warehouses not declared for that company;
- broken foreign-key relationships;
- malformed or unreadable Excel files.

Issues are grouped as:

- **Fatal:** the workbook structure cannot be processed safely.
- **Error:** a row or relationship is invalid and blocks the import.
- **Warning:** a non-blocking observation. Valid generated workbooks normally have no warnings.

The batch importer processes every file independently and creates `import_report.json` with successes, failures, row counts, warnings, and validation details.

## 6. How are duplicate imports handled?

If the target database already contains the workbook's company name, the second import is rejected.

This prevents the same sales, purchases, and other transactions from being counted twice.

This is intentionally simple. A production system would need rules for revised submissions, versions, amendments, and audit history.

## 7. How are shared products and suppliers handled?

Different companies can report the same product or supplier.

- Suppliers are matched using the unique supplier name.
- Products are matched using the exact synthetic product name.
- Each company still receives its own link to the shared product through `company_products`.

The product-name rule is safe only for this controlled fictional dataset because names such as `Synthetic Product 0186` are generated uniquely. A real system would require an approved product ID or master-data process.

## 8. How do we know the import is correct?

`round_trip_validation.py` compares the selected companies in the source and target databases using names and other synthetic business keys—not internal numeric IDs.

It compares:

- number of companies;
- financial records and revenue totals;
- company-product relationships;
- customers;
- sales records and totals;
- imports and purchase totals;
- local purchases;
- inventory;
- exports;
- tenders;
- storage capacity.

It also selects a product with sales and verifies a question equivalent to:

> What were the total sales of Product X across all responding companies in 2026?

In the completed 100-workbook run, all implemented representative field, count, and aggregate comparisons matched. This is strong prototype validation, but it is not a claim that every field in every row was exhaustively compared.

## 9. What can the application do?

The Streamlit application has eight pages:

### Overview

Shows company, product, customer, and transaction counts plus years found in the database.

### Company Explorer

Select a company and inspect its details, financials, activities, products, customers, sales, purchases, imports, exports, inventory, tenders, costs, and storage.

### Product Explorer

Select a product and see which companies reported it, its sales totals, transaction years, imports, and inventory.

### Data Explorer

Choose a dataset and filter it by company, product, year, and row limit.

### Sales / Market Analysis

Select a product, an available year, and optionally a company. The page calculates total sales and shows the supporting records and monthly chart.

### Data Quality / Import Status

This page now has three connected tabs:

- **Database Health** keeps the existing database integrity, foreign-key, and latest import-report information.
- **Data Quality** reports record counts, field null counts/rates, company/year coverage, and arithmetic consistency issues. It includes filters and a CSV download.
- **Anomaly Review** reports explainable statistical review flags with company, product, year, and variable filters plus a CSV download.

These meanings are intentionally different. Import **validation** determines whether a workbook can safely enter the database. A **consistency issue** means component values do not reproduce a stored total within 0.02 currency units. A **statistical review flag** means a value looks unusual within a sufficiently large comparison group. A flag does not prove the value is wrong and is not evidence of anti-competitive conduct.

The arithmetic rules cover sales, local purchases, imports, fixed costs, variable costs, total production costs, tenders, and exports. If a required component is blank, that record is skipped for that rule rather than reported as an arithmetic error. Optional datasets such as imports or tenders are not assumed to exist, and there is no hidden weighted company score.

For sales unit price, sales quantity, import CIF price, and local-purchase unit price, the monitor compares observations for the same product and year. It requires at least 8 observations, finds the median and median absolute deviation (MAD), and flags an absolute robust z-score above 3.5. MAD=0 is handled safely. The method is transparent but cannot understand contract terms, pack sizes, promotions, geography, seasonality, or other commercial context, so every flag requires human interpretation.

### Controlled anomaly demonstration

Create a separate test database with 12 documented anomalies:

```bash
python3 inject_demo_anomalies.py \
  --source eca_demo.db \
  --output eca_demo_anomaly.db \
  --manifest anomaly_manifest.json
```

The script never edits `eca_demo.db` in place. It checks the clean file hash before and after, keeps schema/foreign-key validity, and writes every intended original/modified value and expected detector to `anomaly_manifest.json`. Sparse optional data may require ordinary comparison-support copies; those are listed separately in the manifest.

Open the controlled copy in the app with:

```bash
ECA_DB_PATH=eca_demo_anomaly.db python3 launch_app.py
```

This monitoring supports triage only. It does not detect cartels, classify misconduct, reach legal conclusions, or make enforcement decisions.

### Import Data

Upload one synthetic workbook and run it through the same importer used by the command line.

### System Guide

Read and download this plain-language guide from inside the application.

The app reads year options from the database. It does not assume that every dataset contains 2025 or 2026.

## 10. The easiest way to run the existing demonstration

The project-local virtual environment has already been created. From Terminal:

```bash
cd /path/to/ECA-Internship
python3 launch_app.py
```

Then open the local address printed by the launcher, normally:

```text
http://localhost:8501
```

Always use `python3 launch_app.py`. The launcher deliberately starts Streamlit with `.venv/bin/python`, even when your terminal's `python3` points to Anaconda. It also avoids port-conflict errors by choosing the next available port.

## 11. How to rebuild everything from the beginning

Run these commands from the project directory.

### Install dependencies

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### Generate 1,000 fictional source companies

```bash
.venv/bin/python generate_large_dataset.py --companies 1000 --overwrite
```

### Select 100 companies and generate their workbooks

```bash
.venv/bin/python generate_data_request_workbooks.py --companies 100 --seed 42 --overwrite
```

Using the same source database and seed selects the same companies.

### Create a fresh target and import all workbooks

```bash
.venv/bin/python import_data_requests.py \
  --directory synthetic_data_requests \
  --db eca_demo.db \
  --report import_report.json \
  --create-fresh
```

`--create-fresh` replaces the target database. Do not use it if you intend to retain an existing target.

### Validate the target database

```bash
.venv/bin/python validate_database.py
```

### Compare the target with the source

```bash
.venv/bin/python round_trip_validation.py
```

### Run all automated tests

```bash
.venv/bin/python -m pytest -q
```

### Launch the application

```bash
python3 launch_app.py
```

## 12. What does each Python file do?

| File | Simple description |
|---|---|
| `create_database.py` | Defines and creates the original 19 database tables |
| `populate_database.py` | Adds the original small Phase 1 sample data |
| `reset_database.py` | Deletes the small target database for a clean rebuild |
| `validate_database.py` | Checks database integrity, constraints, and business relationships |
| `sample_queries.py` | Runs the original example SQL queries |
| `generate_large_dataset.py` | Creates the large fictional source database |
| `data_request_mapping.py` | Defines workbook sheets, columns, required fields, and numeric rules |
| `generate_data_request_workbooks.py` | Converts selected source companies into individual Excel files |
| `import_data_requests.py` | Validates and imports one file or a directory of files |
| `round_trip_validation.py` | Compares source and imported results |
| `db.py` | Provides reusable database queries for the application |
| `app.py` | Defines the Streamlit user interface |
| `launch_app.py` | Reliably launches the app with the correct environment and an available port |
| `tests/test_phase2.py` | Automatically checks the complete Phase 2 behavior |

## 13. What was not implemented?

This prototype does not provide:

- real or confidential company data;
- a confirmed internal workbook mapping;
- authentication or user permissions;
- cloud hosting;
- a production database server;
- submission versioning or amendment workflows;
- audit logging;
- fuzzy product matching;
- natural-language-to-SQL;
- production security, backups, or disaster recovery.

Those decisions require confirmed organizational requirements.

## 14. Current verified result

The completed acceptance run produced:

- 1,000 fictional source companies;
- 100 reproducibly selected companies;
- 100 individual Excel workbooks;
- 100 successful imports;
- 0 failed imports;
- 0 rejected rows;
- 0 foreign-key violations;
- 0 mismatches across the implemented representative field, count, and aggregate round-trip checks;
- 16 passing automated tests;
- all eight Streamlit pages executing without test-time exceptions.

The representative sales comparison used `Synthetic Product 0186` in 2026. Both databases returned `9,431,601.10`.
