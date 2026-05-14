from __future__ import annotations

import pytest

from db import SQLiteAdapter, ValidationError
from init_db import create_database


@pytest.fixture()
def adapter(tmp_path):
    db_path = tmp_path / "test_lab.db"
    create_database(db_path, reset=True)
    return SQLiteAdapter(db_path)


def test_search_with_filters_order_and_pagination(adapter: SQLiteAdapter):
    result = adapter.search(
        table="students",
        filters=[{"column": "cohort", "operator": "=", "value": "A1"}],
        columns=["full_name", "score"],
        order_by="score",
        descending=True,
        limit=1,
        offset=0,
    )

    assert result["count"] == 1
    assert result["rows"][0]["full_name"] == "Alice Nguyen"


def test_insert_returns_payload(adapter: SQLiteAdapter):
    result = adapter.insert(
        "students",
        {
            "full_name": "Test User",
            "cohort": "C1",
            "age": 20,
            "score": 8.0,
        },
    )

    assert result["row_id"] > 0
    assert result["values"]["full_name"] == "Test User"


def test_aggregate_avg_by_group(adapter: SQLiteAdapter):
    result = adapter.aggregate(
        table="students",
        metric="avg",
        column="score",
        group_by="cohort",
    )

    cohorts = {row["cohort"] for row in result["rows"]}
    assert {"A1", "B2"}.issubset(cohorts)


def test_reject_unknown_table(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.search(table="unknown", limit=10)


def test_reject_unknown_column(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.search(table="students", columns=["nope"], limit=10)


def test_reject_unsupported_operator(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.search(
            table="students",
            filters=[{"column": "cohort", "operator": "contains", "value": "A1"}],
            limit=10,
        )


def test_reject_empty_insert(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.insert("students", {})


def test_reject_invalid_aggregate(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.aggregate("students", metric="median", column="score")
