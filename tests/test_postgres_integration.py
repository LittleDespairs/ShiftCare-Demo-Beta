import os
import unittest
import uuid
from pathlib import Path

from db_adapter import PostgresConnectionAdapter, apply_postgres_schema


POSTGRES_TEST_DSN = os.getenv("SCHEDULE_APP_POSTGRES_TEST_DSN", "").strip()


@unittest.skipUnless(POSTGRES_TEST_DSN, "SCHEDULE_APP_POSTGRES_TEST_DSN is not set")
class PostgresIntegrationTests(unittest.TestCase):
    def test_postgres_schema_applies_to_disposable_schema(self):
        import psycopg
        from psycopg import sql

        schema_name = f"schedule_app_test_{uuid.uuid4().hex}"
        raw_connection = psycopg.connect(POSTGRES_TEST_DSN)
        try:
            raw_connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
            raw_connection.execute(
                sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name))
            )
            connection = PostgresConnectionAdapter(raw_connection)
            schema_path = Path(__file__).resolve().parents[1] / "docs" / "postgresql" / "001_initial_schema.sql"
            apply_postgres_schema(connection, schema_path)

            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) AS count FROM organizations")
            self.assertEqual(cursor.fetchone()["count"], 1)
            cursor.execute("SELECT COUNT(*) AS count FROM app_settings")
            self.assertGreater(cursor.fetchone()["count"], 0)
        finally:
            raw_connection.rollback()
            raw_connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))
            raw_connection.commit()
            raw_connection.close()
