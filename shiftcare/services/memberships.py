"""Services: memberships for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare import config as app_constants
from shiftcare.services import common as services_common

def find_repair_employee_id_for_member(
    cursor,
    organization_id: int,
    user_id: int,
    user_email: str,
    full_name: str,
) -> int | None:
    normalized_email = str(user_email or "").strip().lower()
    if normalized_email:
        cursor.execute(
            """
            SELECT oi.employee_id
            FROM organization_invitations oi
            JOIN employees e ON e.id = oi.employee_id AND e.organization_id = oi.organization_id
            WHERE oi.organization_id = ?
              AND lower(oi.email) = ?
              AND oi.role = 'employee'
              AND oi.status = 'accepted'
              AND oi.employee_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM organization_memberships linked
                  WHERE linked.organization_id = oi.organization_id
                    AND linked.employee_id = oi.employee_id
                    AND linked.user_id != ?
                    AND linked.status = 'active'
              )
            ORDER BY oi.accepted_at DESC, oi.id DESC
            LIMIT 1
            """,
            (organization_id, normalized_email, user_id),
        )
        invitation = cursor.fetchone()
        if invitation:
            return int(invitation["employee_id"])

    normalized_name = str(full_name or "").strip().lower()
    if not normalized_name:
        return None
    cursor.execute(
        """
        SELECT e.id
        FROM employees e
        WHERE e.organization_id = ?
          AND lower(trim(e.full_name)) = ?
          AND NOT EXISTS (
              SELECT 1
              FROM organization_memberships linked
              WHERE linked.organization_id = e.organization_id
                AND linked.employee_id = e.id
                AND linked.user_id != ?
                AND linked.status = 'active'
          )
        ORDER BY e.id
        """,
        (organization_id, normalized_name, user_id),
    )
    matches = cursor.fetchall()
    if len(matches) == 1:
        return int(matches[0]["id"])
    return None


def repair_employee_membership_links(cursor, current_user: dict) -> bool:
    repaired = False
    user_email = str(current_user.get("email") or "").strip().lower()
    user_id = int(current_user["id"])
    full_name = str(current_user.get("full_name") or "")
    if not user_email and not full_name:
        return False

    for membership in current_user.get("memberships") or []:
        if membership.get("status") != "active" or membership.get("role") != "employee":
            continue
        if membership.get("employee_id"):
            continue

        organization_id = int(membership["organization_id"])
        employee_id = find_repair_employee_id_for_member(cursor, organization_id, user_id, user_email, full_name)
        if employee_id is None:
            continue
        cursor.execute(
            """
            UPDATE organization_memberships
            SET employee_id = ?, updated_at = ?
            WHERE organization_id = ?
              AND user_id = ?
              AND role = 'employee'
              AND status = 'active'
              AND employee_id IS NULL
            """,
            (employee_id, services_common.current_utc_timestamp(), organization_id, current_user["id"]),
        )
        if cursor.rowcount:
            membership["employee_id"] = employee_id
            repaired = True

    return repaired


def repair_organization_employee_membership_links(cursor, organization_id: int) -> int:
    cursor.execute(
        """
        SELECT om.user_id, u.email, u.full_name
        FROM organization_memberships om
        JOIN users u ON u.id = om.user_id
        WHERE om.organization_id = ?
          AND om.role = 'employee'
          AND om.status = 'active'
          AND om.employee_id IS NULL
        ORDER BY om.user_id
        """,
        (organization_id,),
    )
    members = cursor.fetchall()
    repaired_count = 0
    for member in members:
        employee_id = find_repair_employee_id_for_member(
            cursor,
            organization_id,
            int(member["user_id"]),
            str(member["email"] or ""),
            str(member["full_name"] or ""),
        )
        if employee_id is None:
            continue
        cursor.execute(
            """
            UPDATE organization_memberships
            SET employee_id = ?, updated_at = ?
            WHERE organization_id = ?
              AND user_id = ?
              AND role = 'employee'
              AND status = 'active'
              AND employee_id IS NULL
            """,
            (employee_id, services_common.current_utc_timestamp(), organization_id, int(member["user_id"])),
        )
        if cursor.rowcount:
            repaired_count += 1
    return repaired_count


def purge_disabled_organization_accounts(cursor, organization_id: int) -> int:
    cursor.execute(
        """
        SELECT om.user_id, u.email
        FROM organization_memberships om
        JOIN users u ON u.id = om.user_id
        WHERE om.organization_id = ?
          AND om.status = 'disabled'
          AND NOT EXISTS (
              SELECT 1
              FROM organization_memberships active_membership
              WHERE active_membership.user_id = om.user_id
                AND active_membership.status = 'active'
          )
        ORDER BY om.user_id
        """,
        (organization_id,),
    )
    rows = cursor.fetchall()
    for row in rows:
        cursor.execute(
            """
            DELETE FROM organization_invitations
            WHERE organization_id = ?
              AND lower(email) = ?
              AND status != 'pending'
            """,
            (organization_id, str(row["email"] or "").strip().lower()),
        )
        cursor.execute("DELETE FROM users WHERE id = ?", (int(row["user_id"]),))
    return len(rows)


def employee_scope_from_access(access_context: dict | None) -> int | None:
    if not access_context:
        return None
    membership = access_context.get("membership") or {}
    if membership.get("role") != "employee":
        return None
    employee_id = membership.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=403, detail="Employee account is not linked to an employee record")
    return int(employee_id)


def require_employee_position_scope(cursor, employee_id: int, position_id: int | None) -> int | None:
    if position_id is None:
        return None
    cursor.execute(
        """
        SELECT 1
        FROM employee_positions
        WHERE employee_id = ? AND position_id = ?
        """,
        (employee_id, position_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Employees can view only schedules for their assigned positions")
    return position_id


def get_allowed_department_ids(cursor, access_context: dict | None) -> set[int] | None:
    if not access_context:
        return None
    membership = access_context.get("membership") or {}
    role = membership.get("role")
    if role not in app_constants.DEPARTMENT_ACCESS_LIMITED_ROLES:
        return None
    organization_id = membership.get("organization_id")
    user_id = (access_context.get("user") or {}).get("id")
    if not organization_id or not user_id:
        return None
    cursor.execute(
        """
        SELECT department_id
        FROM user_department_access
        WHERE organization_id = ? AND user_id = ?
        ORDER BY department_id
        """,
        (organization_id, user_id),
    )
    rows = cursor.fetchall()
    if not rows:
        cursor.execute(
            "SELECT department_access_mode FROM organization_memberships WHERE organization_id = ? AND user_id = ?",
            (organization_id, user_id),
        )
        scope = cursor.fetchone()
        return set() if scope and scope["department_access_mode"] == "restricted" else None
    return {int(row["department_id"]) for row in rows}


def append_department_access_condition(
    cursor,
    access_context: dict | None,
    conditions: list[str],
    params: list,
    column_sql: str = "p.department_id",
) -> set[int] | None:
    allowed_department_ids = get_allowed_department_ids(cursor, access_context)
    if allowed_department_ids is None:
        return None
    if not allowed_department_ids:
        conditions.append("1 = 0")
        return allowed_department_ids
    placeholders = ",".join(["?"] * len(allowed_department_ids))
    conditions.append(f"{column_sql} IN ({placeholders})")
    params.extend(sorted(allowed_department_ids))
    return allowed_department_ids


def ensure_department_access_for_department(cursor, access_context: dict | None, department_id: int | None) -> None:
    allowed_department_ids = get_allowed_department_ids(cursor, access_context)
    if allowed_department_ids is None or department_id is None:
        return
    if int(department_id) not in allowed_department_ids:
        raise HTTPException(status_code=403, detail="Department access is required")


def ensure_department_access_for_position(cursor, access_context: dict | None, position_id: int | None) -> None:
    if position_id is None:
        return
    allowed_department_ids = get_allowed_department_ids(cursor, access_context)
    if allowed_department_ids is None:
        return
    organization_id = access_context["membership"]["organization_id"] if access_context else None
    cursor.execute(
        """
        SELECT department_id, organization_id
        FROM positions
        WHERE id = ?
        """,
        (position_id,),
    )
    row = cursor.fetchone()
    if not row or (organization_id is not None and int(row["organization_id"]) != int(organization_id)):
        raise HTTPException(status_code=404, detail="Position not found")
    if int(row["department_id"]) not in allowed_department_ids:
        raise HTTPException(status_code=403, detail="Department access is required")


def ensure_department_access_for_employee(cursor, access_context: dict | None, employee_id: int | None) -> None:
    if employee_id is None:
        return
    allowed_department_ids = get_allowed_department_ids(cursor, access_context)
    if allowed_department_ids is None:
        return
    if not allowed_department_ids:
        raise HTTPException(status_code=403, detail="Department access is required")
    organization_id = access_context["membership"]["organization_id"] if access_context else None
    placeholders = ",".join(["?"] * len(allowed_department_ids))
    cursor.execute(
        f"""
        SELECT 1
        FROM employee_positions ep
        JOIN positions p ON p.id = ep.position_id
        WHERE ep.employee_id = ?
          AND p.department_id IN ({placeholders})
          AND (? IS NULL OR p.organization_id = ?)
        LIMIT 1
        """,
        (employee_id, *sorted(allowed_department_ids), organization_id, organization_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Department access is required")


def build_member_department_access(cursor, organization_id: int) -> dict[int, list[dict]]:
    cursor.execute(
        """
        SELECT uda.user_id, d.id, d.public_id, d.name, d.display_order
        FROM user_department_access uda
        JOIN departments d ON d.id = uda.department_id
        WHERE uda.organization_id = ?
        ORDER BY uda.user_id, d.display_order, d.id
        """,
        (organization_id,),
    )
    result: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        result.setdefault(int(row["user_id"]), []).append(
            {
                "id": row["id"],
                "public_id": row["public_id"],
                "name": row["name"],
                "display_order": row["display_order"],
            }
        )
    return result


def require_employee_preference_scope(preference_context: dict | None, employee_id: int) -> None:
    if not preference_context or preference_context["scope"] == "all":
        return
    if preference_context["membership"].get("employee_id") != employee_id:
        raise HTTPException(status_code=403, detail="Employees can manage only their own preferences")


def collect_employee_link_public_ids(cursor, organization_id: int) -> dict[str, list[dict]]:
    cursor.execute(
        """
        SELECT om.user_id, e.public_id AS employee_public_id
        FROM organization_memberships om
        JOIN employees e ON e.id = om.employee_id
        WHERE om.organization_id = ?
          AND om.role = 'employee'
          AND om.status = 'active'
          AND om.employee_id IS NOT NULL
          AND e.public_id IS NOT NULL
          AND e.public_id != ''
        ORDER BY om.user_id
        """,
        (organization_id,),
    )
    memberships = [dict(row) for row in cursor.fetchall()]
    cursor.execute(
        """
        SELECT oi.id AS invitation_id, e.public_id AS employee_public_id
        FROM organization_invitations oi
        JOIN employees e ON e.id = oi.employee_id
        WHERE oi.organization_id = ?
          AND oi.employee_id IS NOT NULL
          AND e.public_id IS NOT NULL
          AND e.public_id != ''
        ORDER BY oi.id
        """,
        (organization_id,),
    )
    invitations = [dict(row) for row in cursor.fetchall()]
    return {"memberships": memberships, "invitations": invitations}


def restore_employee_links_from_public_ids(
    cursor,
    organization_id: int,
    preserved_links: dict[str, list[dict]],
    employee_id_by_public_id: dict[str, int],
    now: str,
) -> dict[str, int]:
    restored_memberships = 0
    restored_invitations = 0
    for link in preserved_links.get("memberships") or []:
        employee_id = employee_id_by_public_id.get(str(link.get("employee_public_id") or ""))
        if not employee_id:
            continue
        cursor.execute(
            """
            UPDATE organization_memberships
            SET employee_id = ?, updated_at = ?
            WHERE organization_id = ?
              AND user_id = ?
              AND role = 'employee'
              AND status = 'active'
            """,
            (employee_id, now, organization_id, int(link["user_id"])),
        )
        restored_memberships += cursor.rowcount
    for link in preserved_links.get("invitations") or []:
        employee_id = employee_id_by_public_id.get(str(link.get("employee_public_id") or ""))
        if not employee_id:
            continue
        cursor.execute(
            """
            UPDATE organization_invitations
            SET employee_id = ?
            WHERE organization_id = ? AND id = ?
            """,
            (employee_id, organization_id, int(link["invitation_id"])),
        )
        restored_invitations += cursor.rowcount
    return {"memberships": restored_memberships, "invitations": restored_invitations}


def preserve_department_access(cursor, organization_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT uda.user_id, d.public_id
        FROM user_department_access uda
        JOIN departments d ON d.id = uda.department_id
        WHERE uda.organization_id = ?
        """,
        (organization_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    # This also protects older databases where the explicit mode was not set by
    # the writer that originally created the allowlist.
    for user_id in {row["user_id"] for row in rows}:
        cursor.execute(
            "UPDATE organization_memberships SET department_access_mode = 'restricted' WHERE organization_id = ? AND user_id = ?",
            (organization_id, user_id),
        )
    return rows


def restore_department_access(cursor, organization_id: int, preserved: list[dict]) -> None:
    cursor.execute("SELECT id, public_id FROM departments WHERE organization_id = ?", (organization_id,))
    department_ids = {row["public_id"]: row["id"] for row in cursor.fetchall()}
    for row in preserved:
        department_id = department_ids.get(row["public_id"])
        if department_id is not None:
            cursor.execute(
                """
                INSERT INTO user_department_access (organization_id, user_id, department_id)
                VALUES (?, ?, ?) ON CONFLICT(organization_id, user_id, department_id) DO NOTHING
                """,
                (organization_id, row["user_id"], department_id),
            )
