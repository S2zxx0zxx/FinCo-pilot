"""Connection-level guard shared by API, workers, MCP and migrations."""

from sqlalchemy import event


RESTORE_PREFIX = "finco_restore_"
QUARANTINE_TABLE = "finco_restore_quarantine"


def assert_runtime_target(database: str | None) -> None:
    if database and database.startswith(RESTORE_PREFIX):
        raise RuntimeError("Isolated restore databases cannot run the application")


def check_quarantine(connection, _record) -> None:
    previous = connection.autocommit
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT to_regclass('public.finco_restore_quarantine')")
        if cursor.fetchone()[0] is not None:
            cursor.execute(
                "SELECT released FROM public.finco_restore_quarantine WHERE singleton = true"
            )
            row = cursor.fetchone()
            if row is None or row[0] is not True:
                raise RuntimeError(
                    "Restored database is quarantined pending disaster recovery release gates"
                )
    finally:
        cursor.close()
        connection.autocommit = previous


def install_quarantine_guard(engine) -> None:
    event.listen(engine.sync_engine, "connect", check_quarantine)
