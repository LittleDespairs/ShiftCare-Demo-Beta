"""Routes: generation for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import AutoGenerateAllScheduleRequest
from schemas import AutoGenerateScheduleRequest
from shiftcare.scheduling import data as scheduling_data
from shiftcare.scheduling import generator as scheduling_generator
from shiftcare.scheduling import settings as scheduling_settings
from shiftcare.services import access as services_access
from shiftcare.services import common as services_common
from shiftcare.services import day_status as services_day_status
from shiftcare.services import licensing as services_licensing
from shiftcare.services import memberships as services_memberships
import database
import schedule_time

router = APIRouter()


@router.post("/api/schedule/auto-generate", tags=["Schedule"])
def auto_generate_schedule(
    request_data: AutoGenerateScheduleRequest,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else 1
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
            (request_data.position_id, organization_id),
            "Position not found",
        )
        services_memberships.ensure_department_access_for_position(cursor, _access, request_data.position_id)
        services_licensing.require_license_capability(cursor, "can_generate_schedule", organization_id)
        result = scheduling_generator.run_auto_generate_for_position(
            connection,
            request_data.position_id,
            request_data.week_start_date,
            request_data.generation_mode,
            sync_day_off_statuses=False,
        )
        connection.commit()
        return result
    finally:
        connection.close()


@router.post("/api/schedule/auto-generate-all", tags=["Schedule"])
def auto_generate_all_schedules(
    request_data: AutoGenerateAllScheduleRequest,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        organization_id = _access["membership"]["organization_id"] if _access else 1
        cursor = connection.cursor()
        services_licensing.require_license_capability(cursor, "can_generate_schedule", organization_id)
        positions = scheduling_generator.load_positions_for_auto_generation(
            cursor,
            organization_id=organization_id,
            department_ids=services_memberships.get_allowed_department_ids(cursor, _access),
        )
        if not positions:
            raise HTTPException(status_code=400, detail="No positions found")

        results: list[dict] = []
        failures: list[dict] = []
        total_created_count = 0
        total_day_off_count = 0
        total_optimization_moved_count = 0

        for position in positions:
            savepoint_name = f"auto_generate_position_{position['id']}"
            cursor.execute(f"SAVEPOINT {savepoint_name}")
            try:
                result = scheduling_generator.run_auto_generate_for_position(
                    connection,
                    position["id"],
                    request_data.week_start_date,
                    request_data.generation_mode,
                    sync_day_off_statuses=False,
                )
            except HTTPException as exc:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                failures.append({
                    "position_id": position["id"],
                    "position_name": position["name"],
                    "detail": exc.detail,
                    "status_code": exc.status_code,
                })
                continue

            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            results.append(result)
            total_created_count += result["created_count"]
            total_day_off_count += result["day_off_count"]
            total_optimization_moved_count += result["optimization_moved_count"]

        # A worker can belong to several positions. Mark free days only after
        # every position has been scheduled, otherwise the first position's
        # generated day_off records block assignments in later positions.
        processed_employee_ids: set[int] = set()
        week_dates = schedule_time.build_week_dates(request_data.week_start_date)
        for result in results:
            employees = [
                employee
                for employee in scheduling_data.load_position_employees(connection, result["position_id"])
                if employee["id"] not in processed_employee_ids
            ]
            processed_employee_ids.update(employee["id"] for employee in employees)
            result["day_off_count"] = services_day_status.sync_generated_day_off_statuses(
                connection, cursor, employees, result["position_id"], week_dates
            )
            total_day_off_count += result["day_off_count"]

        connection.commit()
        return {
            "message": "Auto-generation for all positions finished",
            "week_start_date": request_data.week_start_date,
            "generation_mode": scheduling_settings.normalize_generation_mode(request_data.generation_mode),
            "generated_positions": len(results),
            "failed_positions": len(failures),
            "total_created_count": total_created_count,
            "total_day_off_count": total_day_off_count,
            "total_optimization_moved_count": total_optimization_moved_count,
            "results": results,
            "failures": failures,
        }
    finally:
        connection.close()
