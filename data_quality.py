"""Transparent completeness and arithmetic-consistency checks for the ECA schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_CURRENCY_TOLERANCE = 0.02

# table, id, observed, inputs, expected SQL expression, readable formula
RULES = (
    ("sales", "sale_id", "sales_value_excluding_tax_and_discounts",
     ("sales_quantity", "sale_price_excluding_tax_and_discounts", "customer_discount_value"),
     "x.sales_quantity * x.sale_price_excluding_tax_and_discounts - x.customer_discount_value",
     "sales quantity × sale price excluding tax/discounts − customer discount"),
    ("purchases", "purchase_id", "purchase_value_excluding_tax_and_discounts",
     ("quantity", "price_excluding_tax_and_discounts", "discount_value"),
     "x.quantity * x.price_excluding_tax_and_discounts - x.discount_value",
     "quantity × price excluding tax/discounts − discount"),
    ("imports", "import_id", "purchase_value", ("quantity", "cif_import_price", "discount_value"),
     "x.quantity * x.cif_import_price - x.discount_value", "quantity × CIF import price − discount"),
    ("costs", "cost_id", "total_fixed_cost",
     ("wages_and_salaries", "financing_and_banking_costs", "administrative_expenses", "other_fixed_costs"),
     "x.wages_and_salaries+x.financing_and_banking_costs+x.administrative_expenses+x.other_fixed_costs",
     "wages/salaries + financing/banking + administrative + other fixed costs"),
    ("costs", "cost_id", "total_variable_cost",
     ("drug_purchase_cost", "energy_cost", "transport_cost", "other_variable_costs"),
     "x.drug_purchase_cost+x.energy_cost+x.transport_cost+x.other_variable_costs",
     "drug purchase + energy + transport + other variable costs"),
    ("costs", "cost_id", "total_production_cost", ("total_fixed_cost", "total_variable_cost"),
     "x.total_fixed_cost+x.total_variable_cost", "total fixed cost + total variable cost"),
    ("tender_items", "tender_item_id", "sales_value_excluding_tax", ("sales_quantity", "price_excluding_tax"),
     "x.sales_quantity*x.price_excluding_tax", "sales quantity × price excluding tax"),
    ("exports", "export_id", "export_value_excluding_tax", ("export_quantity", "export_price_excluding_tax"),
     "x.export_quantity*x.export_price_excluding_tax", "export quantity × export price excluding tax"),
)


def _tables(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]


def completeness_statistics(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return factual coverage dimensions; no optional-dataset penalty or overall score."""
    record_counts: list[dict[str, Any]] = []
    null_fields: list[dict[str, Any]] = []
    for table in _tables(conn):
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        record_counts.append({"table": table, "record_count": count})
        for column in conn.execute(f'PRAGMA table_info("{table}")'):
            name = column[1]
            nulls = conn.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{name}" IS NULL').fetchone()[0]
            null_fields.append({"table": table, "field": name, "null_count": nulls,
                                "record_count": count, "null_rate": (nulls / count if count else None)})
    company_coverage = [{"table": table, "companies": count} for table, count in conn.execute("""
        SELECT 'companies',COUNT(*) FROM companies UNION ALL
        SELECT 'company_financials',COUNT(DISTINCT company_id) FROM company_financials UNION ALL
        SELECT 'sales',COUNT(DISTINCT cp.company_id) FROM sales x JOIN company_products cp USING(company_product_id) UNION ALL
        SELECT 'purchases',COUNT(DISTINCT cp.company_id) FROM purchases x JOIN company_products cp USING(company_product_id) UNION ALL
        SELECT 'imports',COUNT(DISTINCT cp.company_id) FROM imports x JOIN company_products cp USING(company_product_id) UNION ALL
        SELECT 'costs',COUNT(DISTINCT cp.company_id) FROM costs x JOIN company_products cp USING(company_product_id) UNION ALL
        SELECT 'exports',COUNT(DISTINCT cp.company_id) FROM exports x JOIN company_products cp USING(company_product_id) UNION ALL
        SELECT 'tenders',COUNT(DISTINCT company_id) FROM tenders
    """)]
    years = [r[0] for r in conn.execute("""SELECT DISTINCT year FROM (
        SELECT year FROM company_financials UNION SELECT year FROM sales UNION SELECT year FROM purchases
        UNION SELECT year FROM imports UNION SELECT year FROM costs UNION SELECT year FROM exports
        UNION SELECT year FROM inventory UNION SELECT year FROM storage_capacity) ORDER BY year""")]
    return {"record_counts": record_counts, "null_fields": null_fields,
            "company_coverage": company_coverage, "year_coverage": years}


def consistency_findings(conn: sqlite3.Connection, tolerance: float = DEFAULT_CURRENCY_TOLERANCE) -> tuple[list[dict[str, Any]], int]:
    findings: list[dict[str, Any]] = []
    checked = 0
    for table, id_col, observed_col, inputs, expression, formula in RULES:
        if table == "tender_items":
            joins = "JOIN tenders t ON t.tender_id=x.tender_id JOIN companies c ON c.company_id=t.company_id JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN products p ON p.product_id=cp.product_id"
            period = "NULL AS year,NULL AS month"
        else:
            joins = "JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN companies c ON c.company_id=cp.company_id JOIN products p ON p.product_id=cp.product_id"
            period = "x.year AS year,x.month AS month"
        required = (observed_col,) + inputs
        where = " AND ".join(f"x.{col} IS NOT NULL" for col in required)
        sql = f"""SELECT x.{id_col} record_identifier,c.company_name company,p.product_name product,
            {period},x.{observed_col} observed_value,{expression} expected_value
            FROM {table} x {joins} WHERE {where}"""
        rows = conn.execute(sql).fetchall()
        checked += len(rows)
        for row in rows:
            difference = float(row[5]) - float(row[6])
            if abs(difference) > tolerance:
                findings.append({"issue_type": "arithmetic_consistency", "dataset": table,
                    "company": row[1], "product": row[2], "year": row[3], "month": row[4],
                    "record_identifier": row[0], "field": observed_col,
                    "expected_value": float(row[6]), "observed_value": float(row[5]),
                    "difference": difference,
                    "reason": f"Observed {observed_col} differs from {formula} by {difference:,.2f}."})
    return findings, checked


def analyze_data_quality(db_path: str | Path, tolerance: float = DEFAULT_CURRENCY_TOLERANCE) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        findings, checked = consistency_findings(conn, tolerance)
        completeness = completeness_statistics(conn)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = [dict(zip(("table", "rowid", "parent", "fk_index"), r))
                        for r in conn.execute("PRAGMA foreign_key_check")]
    return {"currency_tolerance": tolerance, "records_checked": checked, "findings": findings,
            "completeness": completeness, "database_health": {"integrity": integrity,
            "foreign_key_violations": foreign_keys}}
