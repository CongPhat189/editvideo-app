from sqlalchemy.exc import DBAPIError


def pg_error(exc: DBAPIError) -> tuple[str | None, str | None]:
    """(sqlstate, constraint_name) của lỗi Postgres, vd ('23505', 'idx_messages_idempotency')."""
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    return getattr(orig, "sqlstate", None), getattr(diag, "constraint_name", None)
