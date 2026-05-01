import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import license_runtime


def load_local_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Issue a signed ShiftCare license certificate.")
    parser.add_argument("--organization-public-id", required=True)
    parser.add_argument("--customer-legal-name", default="")
    parser.add_argument("--cloud-organization-id", default="")
    parser.add_argument("--branch-id", default="main")
    parser.add_argument("--plan-code", default="team_15")
    parser.add_argument("--employee-limit", type=int, default=15)
    parser.add_argument("--support-cloud-expires-at", required=True, help="YYYY-MM-DD")
    parser.add_argument("--desktop-license-expires-at", default="", help="YYYY-MM-DD, defaults to support expiry")
    parser.add_argument("--trial-started-at", default="")
    parser.add_argument("--trial-expires-at", default="")
    parser.add_argument("--grace-days", type=int, default=license_runtime.DEFAULT_GRACE_DAYS)
    parser.add_argument("--license-id", default="")
    parser.add_argument("--key-id", default="local-hmac-v1")
    parser.add_argument("--status", default="active", choices=["trial", "active", "payment_due", "grace", "expired", "revoked"])
    parser.add_argument("--revoked-at", default="")
    parser.add_argument("--feature", action="append", dest="features", default=["desktop", "employee_portal"])
    parser.add_argument("--output", default="", help="Path for .shiftcare-license JSON output")
    parser.add_argument("--activation-code-output", default="", help="Path for one-time activation code output")
    parser.add_argument("--print-activation-code", action="store_true")
    parser.add_argument("--diagnostics", action="store_true", help="Print non-secret certificate summary")
    return parser.parse_args()


def build_certificate(args: argparse.Namespace) -> dict:
    now = datetime.now(UTC).replace(microsecond=0)
    support_expiry = license_runtime.parse_date(args.support_cloud_expires_at)
    grace_ends_at = support_expiry + timedelta(days=args.grace_days)
    license_id = args.license_id or f"lic_{uuid.uuid4().hex}"
    certificate = {
        "license_id": license_id,
        "organization_public_id": args.organization_public_id,
        "customer_legal_name": args.customer_legal_name,
        "cloud_organization_id": args.cloud_organization_id or None,
        "branch_id": args.branch_id,
        "plan_code": args.plan_code,
        "employee_limit": args.employee_limit,
        "features": sorted(set(args.features or [])),
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "support_cloud_expires_at": support_expiry.isoformat(),
        "desktop_license_expires_at": args.desktop_license_expires_at or support_expiry.isoformat(),
        "grace_ends_at": grace_ends_at.isoformat(),
        "trial_started_at": args.trial_started_at or None,
        "trial_expires_at": args.trial_expires_at or None,
        "status": args.status,
        "revoked_at": args.revoked_at or None,
        "key_id": args.key_id,
        "signature_scheme": "hmac-sha256-v1",
    }
    return {key: value for key, value in certificate.items() if value is not None}


def main() -> int:
    load_local_env()
    args = parse_args()
    secret = os.environ.get("SCHEDULE_APP_LICENSE_SIGNING_SECRET", "").strip()
    if not secret:
        print("SCHEDULE_APP_LICENSE_SIGNING_SECRET is required in environment or .env", file=sys.stderr)
        return 2

    certificate = license_runtime.normalize_certificate(build_certificate(args))
    certificate["signature"] = license_runtime.hmac_signature(certificate, secret)
    activation_code = license_runtime.encode_activation_code(certificate)

    if args.output:
        Path(args.output).write_text(json.dumps(certificate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.activation_code_output:
        Path(args.activation_code_output).write_text(activation_code + "\n", encoding="utf-8")
    if args.print_activation_code:
        print(activation_code)
    if args.diagnostics:
        diagnostics = {
            "license_id": certificate["license_id"],
            "organization_public_id": certificate["organization_public_id"],
            "plan_code": certificate["plan_code"],
            "employee_limit": certificate["employee_limit"],
            "support_cloud_expires_at": certificate.get("support_cloud_expires_at"),
            "grace_ends_at": certificate.get("grace_ends_at"),
            "key_id": certificate.get("key_id"),
            "signature_scheme": certificate.get("signature_scheme"),
            "activation_code_length": len(activation_code),
        }
        print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if not args.output and not args.activation_code_output and not args.print_activation_code and not args.diagnostics:
        print(json.dumps(certificate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
