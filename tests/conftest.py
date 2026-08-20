from __future__ import annotations
import sqlite3
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from create_database import SCHEMA_SQL
from generate_large_dataset import generate_dataset


@pytest.fixture(scope="session")
def source_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("source") / "source.db"
    generate_dataset(path, company_count=12, product_count=20, supplier_count=5, seed=1234, overwrite=True)
    return path


@pytest.fixture
def target_db(tmp_path):
    path = tmp_path / "target.db"
    with sqlite3.connect(path) as conn: conn.executescript(SCHEMA_SQL)
    return path

