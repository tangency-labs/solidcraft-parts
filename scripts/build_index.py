#!/usr/bin/env python3
"""Build index.json from the manifests in libraries/.

    python3 scripts/build_index.py [--out DIR] [--include-examples]

The index is what SolidCraft and workshop.solidcraft.io read. Its layout is described in
docs/index-format.md. Example entries are left out unless --include-examples is given.
The output is the same for the same commit: entries are sorted by id and the time stamp is the
commit's.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_VERSION = 1
REPO = "tangency-labs/solidcraft-parts"
# Manifest fields copied into each index entry, in this order.
FIELDS = ["id", "name", "publisher", "repo", "release", "format", "format_version", "min_solidcraft",
          "license", "description", "tags", "homepage", "tier"]


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def entry(rel: str, data: dict) -> dict:
    out = {k: data[k] for k in FIELDS if k in data}
    out.setdefault("tags", [])
    out.setdefault("homepage", f"https://github.com/{data['repo']}")
    rel_ = data["release"]
    out["download_url"] = f"https://github.com/{data['repo']}/releases/download/{rel_['tag']}/{rel_['asset']}"
    out["manifest"] = rel
    if data.get("example"):
        out["example"] = True
    return out


def build(include_examples: bool) -> dict:
    libraries = []
    for path in sorted((ROOT / "libraries").glob("*/*.json")):
        rel = path.relative_to(ROOT).as_posix()
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("example") and not include_examples:
            continue
        libraries.append(entry(rel, data))
    libraries.sort(key=lambda e: e["id"])
    return {
        "index_version": INDEX_VERSION,
        "generated_at": git("log", "-1", "--format=%cI") or None,
        "source": {"repo": REPO, "commit": git("rev-parse", "HEAD") or None},
        "libraries": libraries,
    }


def write(path: Path, doc: dict) -> None:
    raw = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(raw)
    (path.parent / (path.name + ".sha256")).write_text(f"{hashlib.sha256(raw).hexdigest()}  {path.name}\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="site", help="output folder (default: site)")
    ap.add_argument("--include-examples", action="store_true", help="also write index-with-examples.json")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    doc = build(False)
    write(out / "index.json", doc)
    print(f"index.json: {len(doc['libraries'])} libraries")
    if args.include_examples:
        ex = build(True)
        write(out / "index-with-examples.json", ex)
        print(f"index-with-examples.json: {len(ex['libraries'])} libraries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
