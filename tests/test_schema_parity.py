import re
import unittest
from pathlib import Path

from tests.test_support import database


def _postgres_baseline_schema() -> dict[str, list[str]]:
    schema_path = Path(__file__).resolve().parents[1] / "docs" / "postgresql" / "001_initial_schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    schema: dict[str, list[str]] = {}
    for match in re.finditer(
        r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        table_name = match.group(1)
        body = match.group(2)
        columns: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line:
                continue
            keyword = line.split()[0].upper()
            if keyword in {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}:
                continue
            columns.append(line.split()[0].strip('"'))
        schema[table_name] = columns
    return schema


def _sqlite_runtime_schema() -> dict[str, list[str]]:
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        schema: dict[str, list[str]] = {}
        for row in cursor.fetchall():
            table_name = row["name"]
            cursor.execute(f"PRAGMA table_info({table_name})")
            schema[table_name] = [column["name"] for column in cursor.fetchall()]
        return schema
    finally:
        connection.close()


class SchemaParityTests(unittest.TestCase):
    def test_sqlite_runtime_tables_and_columns_match_postgres_baseline(self):
        sqlite_schema = _sqlite_runtime_schema()
        postgres_schema = _postgres_baseline_schema()

        self.assertEqual(set(sqlite_schema), set(postgres_schema))
        for table_name in sorted(sqlite_schema):
            with self.subTest(table=table_name):
                self.assertEqual(
                    set(sqlite_schema[table_name]),
                    set(postgres_schema[table_name]),
                )

    def test_postgres_baseline_schema_version_matches_runtime_version(self):
        schema_path = Path(__file__).resolve().parents[1] / "docs" / "postgresql" / "001_initial_schema.sql"
        sql = schema_path.read_text(encoding="utf-8")
        match = re.search(
            r"VALUES\s*\(\s*'schema_version'\s*,\s*'(\d+)'\s*\)",
            sql,
            flags=re.IGNORECASE,
        )

        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), database.CURRENT_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
