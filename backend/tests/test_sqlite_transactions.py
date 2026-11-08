import sqlite3
import threading

import pytest
from django.conf import settings


def test_sqlite_transactions_are_immediate():
    assert settings.DATABASES["default"]["OPTIONS"]["transaction_mode"] == "IMMEDIATE"


@pytest.mark.parametrize(
    "mode, expected", [("DEFERRED", "database is locked"), ("IMMEDIATE", "ok")]
)
def test_read_then_write_beside_another_writer(tmp_path, mode, expected):
    path = str(tmp_path / "t.db")
    sqlite3.connect(path).execute("CREATE TABLE t (x)").connection.commit()
    other = sqlite3.connect(
        path, timeout=5, isolation_level=None, check_same_thread=False
    )
    db = sqlite3.connect(path, timeout=5, isolation_level=None)

    if mode == "DEFERRED":
        db.execute("BEGIN DEFERRED")
        db.execute("SELECT count(*) FROM t").fetchall()
        other.execute("BEGIN IMMEDIATE")
    else:
        other.execute("BEGIN IMMEDIATE")
    # The other writer commits shortly; an IMMEDIATE begin waits for it, a deferred upgrade does not.
    threading.Timer(0.3, lambda: other.execute("COMMIT")).start()
    try:
        if mode == "IMMEDIATE":
            db.execute("BEGIN IMMEDIATE")
            db.execute("SELECT count(*) FROM t").fetchall()
        db.execute("INSERT INTO t VALUES (1)")
        db.execute("COMMIT")
        result = "ok"
    except sqlite3.OperationalError as e:
        result = str(e)
        db.execute("ROLLBACK")
    assert result == expected
