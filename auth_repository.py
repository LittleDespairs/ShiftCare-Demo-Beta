import json


def active_user_count(cursor) -> int:
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
    return int(cursor.fetchone()[0])


def create_auth_session(cursor, user_id: int, token_hash: str, expires_at: str) -> None:
    cursor.execute(
        """
        INSERT INTO auth_sessions (user_id, token_hash, expires_at)
        VALUES (?, ?, ?)
        """,
        (user_id, token_hash, expires_at),
    )


def get_session_user_id(cursor, token_hash: str, now: str) -> int | None:
    cursor.execute(
        """
        SELECT user_id
        FROM auth_sessions
        WHERE token_hash = ?
          AND revoked_at IS NULL
          AND expires_at > ?
        """,
        (token_hash, now),
    )
    row = cursor.fetchone()
    return row["user_id"] if row else None


def get_user_context(cursor, user_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT id, email, full_name, status, email_verified, created_at, updated_at, last_login_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    user_row = cursor.fetchone()
    if not user_row:
        return None

    cursor.execute(
        """
        SELECT om.organization_id, o.public_id, o.name, om.role, om.status, om.employee_id
        FROM organization_memberships om
        JOIN organizations o ON o.id = om.organization_id
        WHERE om.user_id = ?
        ORDER BY om.organization_id
        """,
        (user_id,),
    )
    memberships = [
        {
            "organization_id": row["organization_id"],
            "organization_public_id": row["public_id"],
            "organization_name": row["name"],
            "role": row["role"],
            "status": row["status"],
            "employee_id": row["employee_id"],
        }
        for row in cursor.fetchall()
    ]
    return {
        "id": user_row["id"],
        "email": user_row["email"],
        "full_name": user_row["full_name"],
        "status": user_row["status"],
        "email_verified": bool(user_row["email_verified"]),
        "created_at": user_row["created_at"],
        "updated_at": user_row["updated_at"],
        "last_login_at": user_row["last_login_at"],
        "memberships": memberships,
    }


def write_auth_audit_event(
    cursor,
    event_type: str,
    user_id: int | None = None,
    organization_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO auth_audit_events (organization_id, user_id, event_type, metadata_json)
        VALUES (?, ?, ?, ?)
        """,
        (organization_id, user_id, event_type, json.dumps(metadata or {}, ensure_ascii=False)),
    )
