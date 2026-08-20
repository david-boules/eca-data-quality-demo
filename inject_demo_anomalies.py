"""Create a deterministic anomaly-demo copy without modifying the clean source."""

from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def inject_anomalies(source: str | Path, output: str | Path, manifest_path: str | Path) -> list[dict]:
    source, output, manifest_path = Path(source), Path(output), Path(manifest_path)
    if source.resolve() == output.resolve(): raise ValueError("Output must be separate from the clean source database")
    before = file_sha256(source)
    shutil.copy2(source, output)
    manifest: list[dict] = []
    support_records: list[dict] = []
    with sqlite3.connect(output) as conn:
        conn.execute("PRAGMA foreign_keys=ON")

        def change(kind, table, id_col, row_id, column, value, detector):
            original = conn.execute(f"SELECT {column} FROM {table} WHERE {id_col}=?", (row_id,)).fetchone()[0]
            conn.execute(f"UPDATE {table} SET {column}=? WHERE {id_col}=?", (value, row_id))
            manifest.append({"anomaly_type": kind, "table": table,
                "record_business_key": {id_col: row_id}, "field": column,
                "original_value": original, "modified_value": value, "expected_detector": detector})

        # Four statistically extreme observations; dependent calculated values are kept consistent.
        statistical = (("sales", "sale_id", "sale_price_excluding_tax_and_discounts", "extreme sales unit price"),
                       ("sales", "sale_id", "sales_quantity", "extreme sales quantity"),
                       ("imports", "import_id", "cif_import_price", "extreme import CIF price"),
                       ("purchases", "purchase_id", "price_excluding_tax_and_discounts", "extreme local-purchase price"))
        used_sales = set()
        for table, id_col, column, kind in statistical:
            group = conn.execute(f"""SELECT cp.product_id,x.year,COUNT(*) n FROM {table} x
                JOIN company_products cp ON cp.company_product_id=x.company_product_id
                WHERE x.{column} IS NOT NULL GROUP BY cp.product_id,x.year ORDER BY n DESC,cp.product_id,x.year LIMIT 1""").fetchone()
            if not group: raise RuntimeError(f"No source observation available for {kind}")
            product_id, group_year, group_size = group
            # Sparse optional datasets receive ordinary copies solely to form a transparent test group.
            while group_size < 8:
                source_row = conn.execute(f"""SELECT x.* FROM {table} x JOIN company_products cp
                    ON cp.company_product_id=x.company_product_id WHERE cp.product_id=? AND x.year=?
                    AND x.{column} IS NOT NULL ORDER BY x.{id_col} LIMIT 1""", (product_id, group_year)).fetchone()
                columns = [r[1] for r in conn.execute(f"PRAGMA table_info({table})") if r[1] != id_col]
                placeholders = ",".join("?" for _ in columns)
                cursor = conn.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})", tuple(source_row[i + 1] for i in range(len(columns))))
                support_records.append({"table": table, "record_business_key": {id_col: cursor.lastrowid},
                                        "purpose": f"comparison support for {kind}"})
                group_size += 1
            exclude = "" if table != "sales" or not used_sales else "AND x.sale_id NOT IN (%s)" % ",".join("?" * len(used_sales))
            params = (tuple(used_sales) if table == "sales" else ()) + (product_id, group_year)
            row = conn.execute(f"""SELECT x.{id_col},x.{column} FROM {table} x
                JOIN company_products cp ON cp.company_product_id=x.company_product_id
                WHERE x.{column} IS NOT NULL {exclude} AND cp.product_id=? AND x.year=?
                ORDER BY x.{id_col} LIMIT 1""", params).fetchone()
            if not row: raise RuntimeError(f"No defensible comparison group available for {kind}")
            row_id, old = row; new = float(old) * 1000 + 1
            change(kind, table, id_col, row_id, column, new, "statistical_review_flag")
            if table == "sales":
                used_sales.add(row_id)
                qty, price, discount = conn.execute("SELECT sales_quantity,sale_price_excluding_tax_and_discounts,customer_discount_value FROM sales WHERE sale_id=?", (row_id,)).fetchone()
                conn.execute("UPDATE sales SET sales_value_excluding_tax_and_discounts=? WHERE sale_id=?", (qty * price - discount, row_id))
            elif table == "imports":
                qty, price, discount = conn.execute("SELECT quantity,cif_import_price,discount_value FROM imports WHERE import_id=?", (row_id,)).fetchone()
                conn.execute("UPDATE imports SET purchase_value=? WHERE import_id=?", (qty * price - discount, row_id))
            else:
                qty, price, discount = conn.execute("SELECT quantity,price_excluding_tax_and_discounts,discount_value FROM purchases WHERE purchase_id=?", (row_id,)).fetchone()
                conn.execute("UPDATE purchases SET purchase_value_excluding_tax_and_discounts=? WHERE purchase_id=?", (qty * price - discount, row_id))

        arithmetic = (("sales", "sale_id", "sales_value_excluding_tax_and_discounts", "incorrect sales calculated value"),
                      ("purchases", "purchase_id", "purchase_value_excluding_tax_and_discounts", "incorrect purchase calculated value"),
                      ("imports", "import_id", "purchase_value", "incorrect import calculated value"),
                      ("costs", "cost_id", "total_fixed_cost", "incorrect fixed-cost total"),
                      ("costs", "cost_id", "total_variable_cost", "incorrect variable-cost total"),
                      ("costs", "cost_id", "total_production_cost", "incorrect total production cost"),
                      ("tender_items", "tender_item_id", "sales_value_excluding_tax", "incorrect tender calculated value"),
                      ("exports", "export_id", "export_value_excluding_tax", "incorrect export calculated value"))
        used: dict[str, set[int]] = {}
        for table, id_col, column, kind in arithmetic:
            ids = used.setdefault(table, set())
            clause = "" if not ids else f"WHERE {id_col} NOT IN ({','.join('?' * len(ids))})"
            connector = " AND " if clause else " WHERE "
            row = conn.execute(f"SELECT {id_col},{column} FROM {table} {clause}{connector}{column} IS NOT NULL ORDER BY {id_col} LIMIT 1", tuple(ids)).fetchone()
            if not row or row[1] is None: raise RuntimeError(f"No injectable record for {kind}")
            ids.add(row[0]); change(kind, table, id_col, row[0], column, float(row[1]) + 12345.67, "arithmetic_consistency")
        if conn.execute("PRAGMA foreign_key_check").fetchall(): raise RuntimeError("Injection broke foreign-key integrity")
    if file_sha256(source) != before: raise RuntimeError("Clean source database changed")
    payload = {"source_database": str(source), "output_database": str(output),
               "source_sha256_before": before, "source_sha256_after": file_sha256(source), "anomalies": manifest}
    payload["comparison_support_records"] = support_records
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="eca_demo.db"); parser.add_argument("--output", default="eca_demo_anomaly.db")
    parser.add_argument("--manifest", default="anomaly_manifest.json")
    args = parser.parse_args(); records = inject_anomalies(args.source, args.output, args.manifest)
    print(f"Created {args.output} with {len(records)} controlled anomalies; manifest: {args.manifest}")
