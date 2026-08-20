"""Explainable product/year robust statistical review flags."""

from __future__ import annotations
import math
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_MIN_SAMPLE_SIZE = 8
DEFAULT_ROBUST_Z_THRESHOLD = 3.5
MAD_SCALE = 0.6744897501960817

VARIABLES = (
    ("sales", "sale_id", "sale_price_excluding_tax_and_discounts", "sales unit price"),
    ("sales", "sale_id", "sales_quantity", "sales quantity"),
    ("imports", "import_id", "cif_import_price", "import CIF price"),
    ("purchases", "purchase_id", "price_excluding_tax_and_discounts", "local-purchase unit price"),
)


def robust_z_score(value: float, median: float, mad: float) -> float:
    """Return a finite zero at the centre and signed infinity for deviations when MAD is zero."""
    if mad == 0:
        return 0.0 if value == median else math.copysign(math.inf, value - median)
    return MAD_SCALE * (value - median) / mad


def detect_anomalies(db_path: str | Path, min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE,
                     threshold: float = DEFAULT_ROBUST_Z_THRESHOLD) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for table, id_col, column, label in VARIABLES:
            rows = conn.execute(f"""SELECT x.{id_col} record_identifier,c.company_name company,
                p.product_name product,x.year,x.month,x.{column} observed_value
                FROM {table} x JOIN company_products cp ON cp.company_product_id=x.company_product_id
                JOIN companies c ON c.company_id=cp.company_id JOIN products p ON p.product_id=cp.product_id
                WHERE x.{column} IS NOT NULL""").fetchall()
            groups: dict[tuple[str, int], list[sqlite3.Row]] = defaultdict(list)
            for row in rows: groups[(row["product"], row["year"])].append(row)
            for (_, _), group in groups.items():
                if len(group) < min_sample_size: continue
                values = [float(r["observed_value"]) for r in group]
                centre = statistics.median(values)
                mad = statistics.median(abs(v - centre) for v in values)
                for row, value in zip(group, values):
                    score = robust_z_score(value, centre, mad)
                    if abs(score) > threshold:
                        flags.append({"issue_type": "statistical_review_flag", "dataset": table,
                            "record_identifier": row["record_identifier"], "company": row["company"],
                            "product": row["product"], "year": row["year"], "month": row["month"],
                            "variable": label, "observed_value": value, "comparison_group_median": centre,
                            "mad": mad, "robust_z_score": score, "comparison_sample_size": len(group),
                            "reason": f"{label} is beyond the configured robust-z threshold ({threshold}) within the same product/year group. This is a statistical review flag, not proof of incorrect data or anti-competitive conduct."})
    return flags
