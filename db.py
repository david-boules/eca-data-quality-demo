"""Reusable, read-only query layer for the Streamlit application."""

from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATASET_SPECS = {
    "companies": ("companies x", None, None, None),
    "company_financials": ("company_financials x", "x.company_id", None, "x.year"),
    "products": ("products x", None, "x.product_id", None),
    "customers": ("customers x", "x.company_id", None, None),
    "company_products": ("company_products x", "x.company_id", "x.product_id", None),
    "imports": ("imports x JOIN company_products cp ON cp.company_product_id=x.company_product_id", "cp.company_id", "cp.product_id", "x.year"),
    "purchases": ("purchases x JOIN company_products cp ON cp.company_product_id=x.company_product_id", "cp.company_id", "cp.product_id", "x.year"),
    "costs": ("costs x JOIN company_products cp ON cp.company_product_id=x.company_product_id", "cp.company_id", "cp.product_id", "x.year"),
    "sales": ("sales x JOIN company_products cp ON cp.company_product_id=x.company_product_id", "cp.company_id", "cp.product_id", "x.year"),
    "exports": ("exports x JOIN company_products cp ON cp.company_product_id=x.company_product_id", "cp.company_id", "cp.product_id", "x.year"),
    "inventory": ("inventory x JOIN company_products cp ON cp.company_product_id=x.company_product_id", "cp.company_id", "cp.product_id", "x.year"),
    "tenders": ("tenders x", "x.company_id", None, None),
    "storage_capacity": ("storage_capacity x JOIN warehouses w ON w.warehouse_id=x.warehouse_id", "w.company_id", None, "x.year"),
}


class Database:
    def __init__(self, path: str | Path): self.path = Path(path)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path); conn.row_factory = sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON")
        try: yield conn
        finally: conn.close()

    def rows(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.connect() as conn: return [dict(r) for r in conn.execute(sql, params)]

    def scalar(self, sql: str, params: tuple = ()):
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone(); return row[0] if row else None

    def preflight(self, expected_tables: set[str]) -> tuple[bool, str]:
        """Check that the local file is a readable database with the expected schema."""
        if not self.path.exists():
            return False, f"Database file not found: {self.path}"
        try:
            with self.connect() as conn:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    return False, f"SQLite integrity check failed: {integrity}"
                actual = {row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )}
        except sqlite3.Error as exc:
            return False, f"Database could not be opened: {exc}"
        missing = sorted(expected_tables - actual)
        if missing:
            return False, f"Database schema is incomplete. Missing tables: {', '.join(missing)}"
        return True, "ok"

    def companies(self): return self.rows("SELECT company_id,company_name FROM companies ORDER BY company_name")
    def products(self): return self.rows("SELECT product_id,product_name FROM products ORDER BY product_name")
    def years(self):
        return [r["year"] for r in self.rows("""SELECT DISTINCT year FROM (
            SELECT year FROM sales UNION SELECT year FROM imports UNION SELECT year FROM purchases
            UNION SELECT year FROM exports UNION SELECT year FROM inventory UNION SELECT year FROM company_financials
        ) ORDER BY year""")]
    def sales_analysis(self, product_id: int, year: int, company_id: int | None = None):
        sql = """SELECT c.company_name,p.product_name,s.year,s.month,SUM(s.sales_quantity) sales_quantity,
            SUM(s.sales_value_including_tax_and_discounts) total_sales FROM sales s
            JOIN company_products cp ON cp.company_product_id=s.company_product_id
            JOIN companies c ON c.company_id=cp.company_id JOIN products p ON p.product_id=cp.product_id
            WHERE p.product_id=? AND s.year=?"""
        params: list = [product_id, year]
        if company_id is not None: sql += " AND c.company_id=?"; params.append(company_id)
        sql += " GROUP BY c.company_name,p.product_name,s.year,s.month ORDER BY c.company_name,s.month"
        return self.rows(sql, tuple(params))

    def explore(self, table: str, company_id: int | None = None, product_id: int | None = None,
                year: int | None = None, limit: int = 100):
        """Filter an allow-listed dataset in SQL without loading whole tables."""
        if table not in DATASET_SPECS: raise ValueError(f"Unsupported dataset: {table}")
        source, company_col, product_col, year_col = DATASET_SPECS[table]
        clauses, params = [], []
        for value, column in ((company_id, company_col), (product_id, product_col), (year, year_col)):
            if value is not None and column:
                clauses.append(f"{column}=?"); params.append(value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return self.rows(f"SELECT x.* FROM {source}{where} LIMIT ?", (*params, limit))

    @staticmethod
    def explore_capabilities(table: str) -> dict[str, bool]:
        if table not in DATASET_SPECS: raise ValueError(f"Unsupported dataset: {table}")
        _, company_col, product_col, year_col = DATASET_SPECS[table]
        return {"company": company_col is not None, "product": product_col is not None, "year": year_col is not None}

    @staticmethod
    def explore_tables() -> list[str]:
        return list(DATASET_SPECS)
