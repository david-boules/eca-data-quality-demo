from __future__ import annotations
import hashlib
import json
import shutil
import sqlite3

import pytest

from anomaly_detection import detect_anomalies, robust_z_score
from data_quality import RULES, analyze_data_quality
from inject_demo_anomalies import inject_anomalies


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_db(source, target):
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst: src.backup(dst)


def test_clean_generated_database_arithmetic_consistency(source_db):
    report = analyze_data_quality(source_db)
    assert report["findings"] == []
    assert report["records_checked"] > 0
    assert len(report["completeness"]["record_counts"]) == 19


@pytest.mark.parametrize("table,id_col,observed", [(r[0], r[1], r[2]) for r in RULES])
def test_every_arithmetic_rule(source_db, tmp_path, table, id_col, observed):
    path=tmp_path/f"{table}_{observed}.db"; copy_db(source_db,path)
    with sqlite3.connect(path) as conn:
        row=conn.execute(f"SELECT {id_col},{observed} FROM {table} WHERE {observed} IS NOT NULL LIMIT 1").fetchone()
        assert row
        conn.execute(f"UPDATE {table} SET {observed}=? WHERE {id_col}=?",(float(row[1])+100,row[0]))
    found=analyze_data_quality(path)["findings"]
    assert any(x["dataset"]==table and x["field"]==observed and x["record_identifier"]==row[0] for x in found)


def test_null_handling_and_rounding_tolerance(source_db,tmp_path):
    path=tmp_path/"null_rounding.db"; copy_db(source_db,path)
    with sqlite3.connect(path) as conn:
        first=conn.execute("SELECT sale_id,sales_value_excluding_tax_and_discounts FROM sales LIMIT 1").fetchone()
        second=conn.execute("SELECT sale_id,sales_value_excluding_tax_and_discounts FROM sales WHERE sale_id<>? LIMIT 1",(first[0],)).fetchone()
        conn.execute("UPDATE sales SET customer_discount_value=NULL,sales_value_excluding_tax_and_discounts=? WHERE sale_id=?",(float(first[1])+999,first[0]))
        conn.execute("UPDATE sales SET sales_value_excluding_tax_and_discounts=sales_value_excluding_tax_and_discounts+0.01 WHERE sale_id=?",(second[0],))
    ids={x["record_identifier"] for x in analyze_data_quality(path)["findings"] if x["dataset"]=="sales"}
    assert first[0] not in ids and second[0] not in ids


def _stat_db(source_db,tmp_path, values):
    path=tmp_path/f"stats_{len(values)}_{sum(values)}.db"; copy_db(source_db,path)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM sales")
        cp=conn.execute("SELECT company_product_id,company_id FROM company_products LIMIT 1").fetchone()
        customer=conn.execute("SELECT customer_id FROM customers WHERE company_id=? LIMIT 1",(cp[1],)).fetchone()[0]
        for value in values:
            conn.execute("INSERT INTO sales(company_product_id,customer_id,year,month,sale_price_excluding_tax_and_discounts) VALUES(?,?,2026,1,?)",(cp[0],customer,value))
    return path


def test_anomaly_minimum_sample_and_robust_z(source_db,tmp_path):
    assert detect_anomalies(_stat_db(source_db,tmp_path,[10]*6+[1000])) == []
    flags=detect_anomalies(_stat_db(source_db,tmp_path,[9,10,10,10,10,10,11,1000]))
    assert any(f["observed_value"]==1000 and f["comparison_sample_size"]==8 for f in flags)
    assert robust_z_score(12,10,2)==pytest.approx(0.6744897501960817)


def test_mad_zero_is_safe_and_explainable(source_db,tmp_path):
    assert robust_z_score(10,10,0)==0
    assert robust_z_score(11,10,0)==float("inf")
    flags=detect_anomalies(_stat_db(source_db,tmp_path,[10]*7+[11]))
    assert len(flags)==1 and flags[0]["mad"]==0 and flags[0]["observed_value"]==11


def test_controlled_injection_integrity_detection_and_manifest(source_db,tmp_path):
    output=tmp_path/"anomaly.db"; manifest_path=tmp_path/"manifest.json"; before=digest(source_db)
    injected=inject_anomalies(source_db,output,manifest_path); manifest=json.loads(manifest_path.read_text())
    assert digest(source_db)==before==manifest["source_sha256_before"]==manifest["source_sha256_after"]
    assert len(injected)==12 and manifest["anomalies"]==injected
    with sqlite3.connect(output) as conn: assert conn.execute("PRAGMA foreign_key_check").fetchall()==[]
    issues=analyze_data_quality(output)["findings"]; flags=detect_anomalies(output)
    arithmetic=[x for x in injected if x["expected_detector"]=="arithmetic_consistency"]
    statistical=[x for x in injected if x["expected_detector"]=="statistical_review_flag"]
    assert all(any(f["dataset"]==x["table"] and f["record_identifier"] in x["record_business_key"].values() for f in issues) for x in arithmetic)
    assert all(any(f["dataset"]==x["table"] and f["record_identifier"] in x["record_business_key"].values() for f in flags) for x in statistical)


def test_hosted_demo_uses_fixed_synthetic_database_and_disables_import(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setenv("ECA_HOSTED_DEMO","1")
    monkeypatch.delenv("ECA_DB_PATH",raising=False)
    app=AppTest.from_file(str(root/"app.py"),default_timeout=20).run()
    assert not app.exception
    assert "Import Data" not in app.sidebar.radio[0].options
    assert not app.sidebar.text_input
