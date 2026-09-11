"""Generate/check committed packaging metadata from release_config.APP_VERSION.

Run after changing APP_VERSION; use --check in CI/builds to reject stale files.
This tool does not import the application or open a database.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from release_config import APP_VERSION


def generated_files() -> dict[Path, str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+_beta", APP_VERSION):
        raise ValueError("APP_VERSION must use major.minor.patch_beta")
    display = APP_VERSION.replace("_", "-")
    numeric = APP_VERSION.removesuffix("_beta") + ".0"
    version_tuple = ", ".join(numeric.split("."))
    result = {}
    for demo in (False, True):
        prefix = "ShiftCare_Demo" if demo else "ShiftCare"
        metadata = ROOT / ("version_info_demo.txt" if demo else "version_info.txt")
        content = metadata.read_text(encoding="utf-8")
        content = re.sub(r"(filevers|prodvers)=\([\d, ]+\)", lambda m: f"{m[1]}=({version_tuple})", content)
        content = re.sub(r"StringStruct\('FileVersion', '[^']+'\)", f"StringStruct('FileVersion', '{numeric}')", content)
        content = re.sub(r"StringStruct\('ProductVersion', '[^']+'\)", f"StringStruct('ProductVersion', '{display}')", content)
        content = re.sub(r"StringStruct\('OriginalFilename', '[^']+'\)", f"StringStruct('OriginalFilename', '{prefix}_{APP_VERSION}.exe')", content)
        result[metadata] = content

        installer = ROOT / "installer" / ("ScheduleAppDemo.iss" if demo else "ScheduleApp.iss")
        content = installer.read_text(encoding="utf-8")
        defines = {"MyAppVersion": display, "MyAppExeName": f"{prefix}_{APP_VERSION}.exe", "MyAppDistDir": f"..\\dist\\{prefix}_{APP_VERSION}"}
        for key, value in defines.items():
            content = re.sub(rf'^#define {key} "[^"]+"', lambda _: f'#define {key} "{value}"', content, flags=re.M)
        content = re.sub(r"^(VersionInfoProductVersion|VersionInfoVersion)=.+$", lambda m: f"{m[1]}={numeric}", content, flags=re.M)
        result[installer] = content

    android = ROOT / "android/app/build.gradle"
    content = android.read_text(encoding="utf-8")
    content = re.sub(r'versionName "[^"]+"', f'versionName "{display}-tablet-current"', content)
    result[android] = content

    worker = ROOT / "static/service-worker.js"
    content = worker.read_text(encoding="utf-8")
    pages = ["/", "/login", "/schedule", "/weekly-preferences", "/organization", "/feedback", "/guide", "/accept-invitation", "/reset-password", "/verify-email"]
    optional_pages = ["/settings", "/employees", "/departments", "/positions", "/employee-positions", "/shift-templates", "/coverage-requirements", "/support"]
    assets = [f"/{path.relative_to(ROOT).as_posix()}?v={APP_VERSION}" for folder in ("css", "js") for path in sorted((ROOT / "static" / folder).glob("*")) if path.suffix in (".css", ".js")]
    assets += ["/manifest.webmanifest", "/static/icons/app-icon.svg", "/static/offline.html"]
    prefix = "// Generated release asset list: python tools/sync_release_metadata.py\n"
    prefix += f'const APP_VERSION = "{APP_VERSION}";\nconst CACHE_NAME = `shiftcare-${{APP_VERSION}}`;\n\n'
    prefix += "const SHELL_ASSETS = " + json.dumps(pages + assets, ensure_ascii=False, indent=2) + ";\n\n"
    prefix += "const OPTIONAL_PAGES = " + json.dumps(optional_pages, indent=2) + ";\n\n"
    result[worker] = prefix + content[content.index('self.addEventListener("install"'):]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = []
    for path, expected in generated_files().items():
        if path.read_text(encoding="utf-8") != expected:
            changed.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.write_text(expected, encoding="utf-8")
    if changed:
        print(("Stale release metadata: " if args.check else "Updated release metadata: ") + ", ".join(changed))
    return int(args.check and bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
