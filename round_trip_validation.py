"""Compare imported target data with the selected source companies by business key."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


TABLE_METRICS = {
    "company_financials": ("COUNT(*)", "COALESCE(SUM(annual_revenue),0)"),
    "company_products": ("COUNT(*)", "0"),
    "customers": ("COUNT(*)", "0"),
    "sales": ("COUNT(*)", "COALESCE(SUM(sales_value_including_tax_and_discounts),0)"),
    "imports": ("COUNT(*)", "COALESCE(SUM(purchase_value),0)"),
    "purchases": ("COUNT(*)", "COALESCE(SUM(purchase_value_including_tax_and_discounts),0)"),
    "inventory": ("COUNT(*)", "COALESCE(SUM(inventory_value_including_tax),0)"),
    "exports": ("COUNT(*)", "COALESCE(SUM(export_value_including_tax),0)"),
    "tenders": ("COUNT(DISTINCT t.tender_id)", "COALESCE(SUM(ti.sales_value_including_tax),0)"),
    "storage_capacity": ("COUNT(*)", "COALESCE(SUM(sc.storage_capacity),0)"),
}


FIELD_CHECK_QUERIES = {
    "company": """SELECT company_name,market_or_sector,establishment_year,company_type,contact_details
        FROM companies WHERE company_name=?""",
    "financial": """SELECT c.company_name,f.year,f.issued_capital,f.paid_in_capital,f.total_assets,
        f.annual_revenue,f.total_liabilities,f.total_expenses
        FROM company_financials f JOIN companies c ON c.company_id=f.company_id
        WHERE c.company_name=? ORDER BY f.year LIMIT 1""",
    "product": """SELECT c.company_name,p.product_name,p.brand_name,p.product_specifications,
        p.license_holder_company,p.manufacturer_company,p.product_source,p.product_type,
        p.dispensing_method,p.registration_status,p.registration_authority,p.therapeutic_purpose,
        p.active_ingredient FROM company_products cp
        JOIN companies c ON c.company_id=cp.company_id JOIN products p ON p.product_id=cp.product_id
        WHERE c.company_name=? ORDER BY p.product_name LIMIT 1""",
    "customer": """SELECT c.company_name,cu.customer_code,cu.customer_name,cu.customer_type,
        cu.branch_area,cu.governorate,cu.relationship_start_date,cu.relationship_end_date,cu.phone_number
        FROM customers cu JOIN companies c ON c.company_id=cu.company_id
        WHERE c.company_name=? ORDER BY cu.customer_code LIMIT 1""",
    "sale": """SELECT c.company_name,p.product_name,cu.customer_code,s.year,s.month,s.sales_quantity,
        s.returned_quantity,s.sale_price_excluding_tax_and_discounts,s.customer_discount_value,
        s.sales_value_excluding_tax_and_discounts,s.sales_value_including_tax_and_discounts
        FROM sales s JOIN company_products cp ON cp.company_product_id=s.company_product_id
        JOIN companies c ON c.company_id=cp.company_id JOIN products p ON p.product_id=cp.product_id
        JOIN customers cu ON cu.customer_id=s.customer_id WHERE c.company_name=?
        ORDER BY p.product_name,cu.customer_code,s.year,s.month,s.sales_quantity,s.sales_value_including_tax_and_discounts LIMIT 1""",
    "storage": """SELECT c.company_name,w.warehouse_name,w.warehouse_area,sc.year,sc.storage_capacity
        FROM storage_capacity sc JOIN warehouses w ON w.warehouse_id=sc.warehouse_id
        JOIN companies c ON c.company_id=w.company_id WHERE c.company_name=?
        ORDER BY w.warehouse_name,sc.year LIMIT 1""",
    "inventory": """SELECT c.company_name,w.warehouse_name,p.product_name,i.year,i.inventory_quantity,
        i.inventory_value_excluding_tax,i.inventory_value_including_tax FROM inventory i
        JOIN warehouses w ON w.warehouse_id=i.warehouse_id JOIN companies c ON c.company_id=w.company_id
        JOIN company_products cp ON cp.company_product_id=i.company_product_id
        JOIN products p ON p.product_id=cp.product_id WHERE c.company_name=?
        ORDER BY w.warehouse_name,p.product_name,i.year LIMIT 1""",
}


def _canonical_row(row: tuple | None) -> tuple | None:
    if row is None:
        return None
    return tuple(round(value, 6) if isinstance(value, float) else value for value in row)


def _representative_field_checks(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    company_names: list[str],
) -> tuple[dict, list[dict]]:
    performed = skipped = 0
    by_type = {name: 0 for name in FIELD_CHECK_QUERIES}
    mismatches: list[dict] = []
    for company_name in company_names:
        for check_name, query in FIELD_CHECK_QUERIES.items():
            expected = _canonical_row(source.execute(query, (company_name,)).fetchone())
            actual = _canonical_row(target.execute(query, (company_name,)).fetchone())
            if expected is None and actual is None:
                skipped += 1
                continue
            performed += 1
            by_type[check_name] += 1
            if expected != actual:
                mismatches.append({
                    "company": company_name,
                    "metric": f"representative_field:{check_name}",
                    "source": expected,
                    "target": actual,
                })
    summary = {
        "passed": not mismatches,
        "performed": performed,
        "skipped_absent_in_both": skipped,
        "by_type": by_type,
    }
    return summary, mismatches


def _metric(conn: sqlite3.Connection, table: str, company_name: str) -> tuple[int, float]:
    count, total = TABLE_METRICS[table]
    if table == "company_financials":
        joins = "JOIN companies c ON c.company_id=x.company_id"; source = "company_financials x"
    elif table in {"company_products", "customers"}:
        joins = "JOIN companies c ON c.company_id=x.company_id"; source = f"{table} x"
    elif table in {"sales", "imports", "purchases", "exports"}:
        source = f"{table} x"; joins = "JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN companies c ON c.company_id=cp.company_id"
    elif table == "inventory":
        source = "inventory x"; joins = "JOIN warehouses w ON w.warehouse_id=x.warehouse_id JOIN companies c ON c.company_id=w.company_id"
    elif table == "tenders":
        source = "tenders t"; joins = "JOIN companies c ON c.company_id=t.company_id LEFT JOIN tender_items ti ON ti.tender_id=t.tender_id"
    else:
        source = "storage_capacity sc"; joins = "JOIN warehouses w ON w.warehouse_id=sc.warehouse_id JOIN companies c ON c.company_id=w.company_id"
    row = conn.execute(f"SELECT {count},{total} FROM {source} {joins} WHERE c.company_name=?", (company_name,)).fetchone()
    return int(row[0]), round(float(row[1] or 0), 2)


def validate_round_trip(source_db: Path, target_db: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names = [x["company_name"] for x in manifest["companies"]]
    mismatches = []
    field_summary = {"passed": False, "performed": 0, "skipped_absent_in_both": 0, "by_type": {}}
    with sqlite3.connect(source_db) as source, sqlite3.connect(target_db) as target:
        target_count = target.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        if target_count != len(names):
            mismatches.append({"metric": "company_count", "source": len(names), "target": target_count})
        for name in names:
            for table in TABLE_METRICS:
                expected, actual = _metric(source, table, name), _metric(target, table, name)
                if expected != actual:
                    mismatches.append({"company": name, "metric": table, "source": expected, "target": actual})
        field_summary, field_mismatches = _representative_field_checks(source, target, names)
        mismatches.extend(field_mismatches)
        row = target.execute("""SELECT p.product_name,s.year,SUM(s.sales_value_including_tax_and_discounts)
            FROM sales s JOIN company_products cp ON cp.company_product_id=s.company_product_id
            JOIN products p ON p.product_id=cp.product_id GROUP BY p.product_name,s.year ORDER BY COUNT(*) DESC LIMIT 1""").fetchone()
        analytical = None
        if row:
            product, year, target_total = row
            placeholders = ",".join("?" for _ in names)
            source_total = source.execute(f"""SELECT COALESCE(SUM(s.sales_value_including_tax_and_discounts),0)
                FROM sales s JOIN company_products cp ON cp.company_product_id=s.company_product_id
                JOIN products p ON p.product_id=cp.product_id JOIN companies c ON c.company_id=cp.company_id
                WHERE p.product_name=? AND s.year=? AND c.company_name IN ({placeholders})""", (product, year, *names)).fetchone()[0]
            analytical = {"product": product, "year": year, "source_total": round(source_total, 2),
                          "target_total": round(target_total, 2), "match": round(source_total, 2) == round(target_total, 2)}
            if not analytical["match"]: mismatches.append({"metric": "representative_sales", **analytical})
    return {"passed": not mismatches, "selected_companies": len(names), "mismatches": mismatches,
            "representative_field_checks": field_summary, "representative_sales_query": analytical}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-db", type=Path, default=Path("eca_demo_large.db"))
    p.add_argument("--target-db", type=Path, default=Path("eca_demo.db"))
    p.add_argument("--manifest", type=Path, default=Path("synthetic_data_requests/selection_manifest.json"))
    p.add_argument("--report", type=Path, default=Path("round_trip_report.json"))
    a = p.parse_args(); report = validate_round_trip(a.source_db, a.target_db, a.manifest)
    a.report.write_text(json.dumps(report, indent=2), encoding="utf-8"); print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__": main()
