from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SUPPORTED_OPERATORS = {"=", "!=", "<", ">", "<=", ">=", "like", "in"}
SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        self._assert_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({self._quote_identifier(table)})").fetchall()

        schema: list[dict[str, Any]] = []
        for row in rows:
            schema.append(
                {
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "pk": bool(row["pk"]),
                }
            )
        return schema

    def get_database_schema(self) -> dict[str, list[dict[str, Any]]]:
        return {table: self.get_table_schema(table) for table in self.list_tables()}

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | list[str] | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        valid_columns = self._get_table_columns(table)
        selected_columns = columns or valid_columns
        self._assert_columns(selected_columns, valid_columns)

        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError("limit must be a positive integer")
        if limit > 1000:
            raise ValidationError("limit must be <= 1000")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative integer")

        where_sql, where_params = self._build_where(filters, valid_columns)
        order_sql = self._build_order_clause(order_by, valid_columns, descending)

        sql = (
            "SELECT "
            + ", ".join(self._quote_identifier(col) for col in selected_columns)
            + f" FROM {self._quote_identifier(table)}"
            + where_sql
            + order_sql
            + " LIMIT ? OFFSET ?"
        )
        params = [*where_params, limit, offset]

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        result_rows = [dict(row) for row in rows]
        return {
            "table": table,
            "columns": selected_columns,
            "rows": result_rows,
            "count": len(result_rows),
            "limit": limit,
            "offset": offset,
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, dict) or not values:
            raise ValidationError("values must be a non-empty object")

        valid_columns = self._get_table_columns(table)
        columns = list(values.keys())
        self._assert_columns(columns, valid_columns)

        sql = (
            f"INSERT INTO {self._quote_identifier(table)}"
            + " ("
            + ", ".join(self._quote_identifier(col) for col in columns)
            + ") VALUES ("
            + ", ".join("?" for _ in columns)
            + ")"
        )
        params = [values[col] for col in columns]

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            row_id = cursor.lastrowid

        return {"table": table, "row_id": row_id, "values": values}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]:
        valid_columns = self._get_table_columns(table)
        normalized_metric = metric.lower()
        if normalized_metric not in SUPPORTED_METRICS:
            raise ValidationError(f"unsupported metric '{metric}'")

        group_columns = self._normalize_group_by(group_by)
        self._assert_columns(group_columns, valid_columns)

        metric_expr = self._build_metric_expr(normalized_metric, column, valid_columns)
        where_sql, where_params = self._build_where(filters, valid_columns)

        select_parts = [*(self._quote_identifier(col) for col in group_columns), f"{metric_expr} AS value"]
        group_sql = ""
        if group_columns:
            group_sql = " GROUP BY " + ", ".join(self._quote_identifier(col) for col in group_columns)

        sql = (
            "SELECT "
            + ", ".join(select_parts)
            + f" FROM {self._quote_identifier(table)}"
            + where_sql
            + group_sql
        )

        with self.connect() as conn:
            rows = conn.execute(sql, where_params).fetchall()

        return {
            "table": table,
            "metric": normalized_metric,
            "column": column,
            "group_by": group_columns,
            "rows": [dict(row) for row in rows],
        }

    def _assert_table(self, table: str) -> None:
        if table not in self.list_tables():
            raise ValidationError(f"unknown table '{table}'")

    def _get_table_columns(self, table: str) -> list[str]:
        self._assert_table(table)
        schema = self.get_table_schema(table)
        return [col["name"] for col in schema]

    def _assert_columns(self, columns: list[str], valid_columns: list[str]) -> None:
        for column in columns:
            if column not in valid_columns:
                raise ValidationError(f"unknown column '{column}'")

    def _build_where(
        self,
        filters: list[dict[str, Any]] | None,
        valid_columns: list[str],
    ) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        if not isinstance(filters, list):
            raise ValidationError("filters must be a list")

        clauses: list[str] = []
        params: list[Any] = []

        for item in filters:
            if not isinstance(item, dict):
                raise ValidationError("each filter must be an object")

            column = item.get("column")
            operator = str(item.get("operator", "=")).lower()
            value = item.get("value")

            if column not in valid_columns:
                raise ValidationError(f"unknown column '{column}'")
            if operator not in SUPPORTED_OPERATORS:
                raise ValidationError(f"unsupported operator '{operator}'")

            quoted_column = self._quote_identifier(column)

            if operator == "in":
                if not isinstance(value, (list, tuple)) or not value:
                    raise ValidationError("operator 'in' requires a non-empty list value")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{quoted_column} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{quoted_column} {operator.upper()} ?")
                params.append(value)

        return " WHERE " + " AND ".join(clauses), params

    def _build_order_clause(
        self,
        order_by: str | list[str] | None,
        valid_columns: list[str],
        descending: bool,
    ) -> str:
        if not order_by:
            return ""

        if isinstance(order_by, str):
            columns = [order_by]
        elif isinstance(order_by, list):
            columns = order_by
        else:
            raise ValidationError("order_by must be a string or list of strings")

        self._assert_columns(columns, valid_columns)

        direction = "DESC" if descending else "ASC"
        return " ORDER BY " + ", ".join(f"{self._quote_identifier(col)} {direction}" for col in columns)

    def _normalize_group_by(self, group_by: str | list[str] | None) -> list[str]:
        if group_by is None:
            return []
        if isinstance(group_by, str):
            return [group_by]
        if isinstance(group_by, list):
            return group_by
        raise ValidationError("group_by must be a string or list of strings")

    def _build_metric_expr(self, metric: str, column: str | None, valid_columns: list[str]) -> str:
        if metric == "count":
            if column is None:
                return "COUNT(*)"
            if column not in valid_columns:
                raise ValidationError(f"unknown column '{column}'")
            return f"COUNT({self._quote_identifier(column)})"

        if column is None:
            raise ValidationError(f"metric '{metric}' requires a column")
        if column not in valid_columns:
            raise ValidationError(f"unknown column '{column}'")

        return f"{metric.upper()}({self._quote_identifier(column)})"

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'
