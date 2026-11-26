#!/usr/bin/env python3
"""Refresh schema/spdx.json from the SPDX licence list (github.com/spdx/license-list-data)."""

import json
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/spdx/license-list-data/main/json/"
OUT = Path(__file__).resolve().parent.parent / "schema" / "spdx.json"


def fetch(name: str) -> dict:
    with urllib.request.urlopen(BASE + name, timeout=60) as r:
        return json.load(r)


def main() -> None:
    lic = fetch("licenses.json")
    exc = fetch("exceptions.json")
    out = {
        "_comment": "SPDX license and exception ids, from github.com/spdx/license-list-data "
                    "(json/licenses.json, json/exceptions.json). Refresh with scripts/update_spdx.py.",
        "license_list_version": lic.get("licenseListVersion"),
        "licenses": sorted(x["licenseId"] for x in lic["licenses"] if not x.get("isDeprecatedLicenseId")),
        "deprecated_licenses": sorted(x["licenseId"] for x in lic["licenses"] if x.get("isDeprecatedLicenseId")),
        "exceptions": sorted(x["licenseExceptionId"] for x in exc["exceptions"] if not x.get("isDeprecatedLicenseId")),
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"{len(out['licenses'])} licences, {len(out['exceptions'])} exceptions")


if __name__ == "__main__":
    main()
